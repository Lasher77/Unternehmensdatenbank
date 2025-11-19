"""Salesforce integration endpoints."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Mapping
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..db import get_db
from ..dependencies.auth import require_salesforce_bearer_token
from ..schemas.salesforce_match import (
    SalesforceMatchItem,
    SalesforceMatchRequest,
    SalesforceMatchResponse,
    SalesforceMatchedCompany,
    SalesforceMatchThresholds,
)
from ..utils.country_normalization import normalize_country_code

router = APIRouter(prefix="/api/salesforce", tags=["salesforce"])

logger = logging.getLogger(__name__)

MAX_CANDIDATES = 50

_BASE_COMPANY_SELECT = """
SELECT
    source_id,
    COALESCE(name_norm, raw_name) AS name,
    COALESCE(email, data->>'email') AS email,
    street,
    postal_code,
    city,
    country,
    register_id,
    COALESCE(data->>'vat_id', data->>'vatId') AS vat_id,
    COALESCE(website, data->>'website') AS website,
    COALESCE(phone, data->>'phone') AS phone,
    COALESCE(
        revenue,
        CASE
            WHEN NULLIF(btrim(data->>'revenue'), '') ~ '^[-+]?[0-9]+(\\.[0-9]+)?$'
            THEN (data->>'revenue')::double precision
            ELSE NULL
        END
    ) AS revenue,
    status
FROM companies
"""


@dataclass
class NormalizedQuery:
    """Normalized values from a ``SalesforceMatchQuery`` for matching/scoring."""

    name: str | None = None
    name_norm: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    country_code: str | None = None
    website: str | None = None
    domain: str | None = None
    domain_sld: str | None = None
    phone: str | None = None
    phone_digits: str | None = None
    register_id: str | None = None
    vat_id: str | None = None


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_name(value: str | None) -> str | None:
    cleaned = _clean_str(value)
    if not cleaned:
        return None
    return " ".join(cleaned.split()).lower()


def _normalize_register_id(value: str | None) -> str | None:
    cleaned = _clean_str(value)
    if not cleaned:
        return None
    return cleaned.upper()


def _normalize_vat_id(value: str | None) -> str | None:
    cleaned = _clean_str(value)
    if not cleaned:
        return None
    return re.sub(r"[^A-Z0-9]", "", cleaned.upper()) or None


def _normalize_phone_digits(value: str | None) -> str | None:
    cleaned = _clean_str(value)
    if not cleaned:
        return None
    digits = re.sub(r"\D", "", cleaned)
    return digits or None


def _extract_domain(value: str | None) -> str | None:
    cleaned = _clean_str(value)
    if not cleaned:
        return None
    candidate = cleaned
    if "://" not in candidate:
        candidate = f"http://{candidate}"
    parsed = urlparse(candidate)
    domain = parsed.netloc or parsed.path
    domain = domain.lower()
    if ":" in domain:
        domain = domain.split(":", 1)[0]
    domain = domain.lstrip("www.")
    domain = domain.strip("/")
    return domain or None


def _extract_second_level_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    parts = domain.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def _normalize_query_model(match_request: SalesforceMatchRequest) -> NormalizedQuery:
    q = match_request.query
    name = _clean_str(q.name)
    website = _clean_str(q.website)
    country = _clean_str(q.country)
    normalized_country = normalize_country_code(country) if country else None
    domain = _extract_domain(website)
    return NormalizedQuery(
        name=name,
        name_norm=_normalize_name(name),
        street=_clean_str(q.street),
        postal_code=_clean_str(q.postal_code),
        city=_clean_str(q.city),
        country=country,
        country_code=normalized_country,
        website=website,
        domain=domain,
        domain_sld=_extract_second_level_domain(domain),
        phone=_clean_str(q.phone),
        phone_digits=_normalize_phone_digits(q.phone),
        register_id=_normalize_register_id(q.register_id),
        vat_id=_normalize_vat_id(q.vat_id),
    )


def _has_query_fields(match_request: SalesforceMatchRequest) -> bool:
    for value in match_request.query.model_dump().values():
        if isinstance(value, str) and value.strip():
            return True
        if value not in (None, [], {}):
            return True
    return False


def _row_to_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(row)
    data["source_id"] = str(data["source_id"])
    return data


def _add_candidates(
    rows: list[Mapping[str, Any]], candidates: dict[str, dict[str, Any]]
) -> None:
    for row in rows:
        candidate = _row_to_candidate(row)
        source_id = candidate["source_id"]
        if source_id in candidates:
            continue
        candidates[source_id] = candidate
        if len(candidates) >= MAX_CANDIDATES:
            break


def _query_by_register_id(
    db: Connection, register_id: str, limit: int
) -> list[Mapping[str, Any]]:
    if limit <= 0:
        return []
    sql = text(
        _BASE_COMPANY_SELECT
        + " WHERE register_id IS NOT NULL AND UPPER(register_id) = :register_id"
        + " LIMIT :limit"
    )
    return (
        db.execute(sql, {"register_id": register_id, "limit": limit})
        .mappings()
        .all()
    )


def _query_by_vat_id(db: Connection, vat_id: str, limit: int) -> list[Mapping[str, Any]]:
    if limit <= 0:
        return []
    sql = text(
        _BASE_COMPANY_SELECT
        + " WHERE COALESCE(data->>'vat_id', data->>'vatId') IS NOT NULL"
        + " AND UPPER(COALESCE(data->>'vat_id', data->>'vatId')) = :vat_id"
        + " LIMIT :limit"
    )
    return (
        db.execute(sql, {"vat_id": vat_id, "limit": limit}).mappings().all()
    )


def _query_by_filters(
    db: Connection, normalized: NormalizedQuery, limit: int
) -> list[Mapping[str, Any]]:
    if limit <= 0:
        return []
    filters: list[str] = []
    params: dict[str, Any] = {"limit": limit}

    if normalized.name:
        filters.append(
            "((name_norm ILIKE :name_like) OR (raw_name ILIKE :name_like))"
        )
        params["name_like"] = f"%{normalized.name}%"

    if normalized.city:
        filters.append("LOWER(city) = :city")
        params["city"] = normalized.city.lower()

    if normalized.postal_code:
        filters.append("postal_code = :postal_code")
        params["postal_code"] = normalized.postal_code

    if normalized.country_code:
        filters.append("UPPER(country) = :country")
        params["country"] = normalized.country_code

    if normalized.street:
        filters.append("street ILIKE :street")
        params["street"] = f"%{normalized.street}%"

    if normalized.domain:
        filters.append(
            "split_part("
            "REGEXP_REPLACE(LOWER(COALESCE(data->>'website','')), '^https?://', ''),"
            " '/', 1) LIKE :domain_pattern"
        )
        params["domain_pattern"] = f"%{normalized.domain}%"

    if normalized.phone_digits:
        filters.append(
            "REGEXP_REPLACE(COALESCE(data->>'phone',''), '[^0-9]', '', 'g') = :phone"
        )
        params["phone"] = normalized.phone_digits

    if not filters:
        return []

    sql = text(
        _BASE_COMPANY_SELECT
        + " WHERE "
        + " AND ".join(filters)
        + " ORDER BY updated_at DESC LIMIT :limit"
    )
    return db.execute(sql, params).mappings().all()


def _collect_candidates(db: Connection, normalized: NormalizedQuery) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}

    if normalized.register_id:
        rows = _query_by_register_id(db, normalized.register_id, MAX_CANDIDATES)
        _add_candidates(rows, candidates)

    if len(candidates) < MAX_CANDIDATES and normalized.vat_id:
        rows = _query_by_vat_id(db, normalized.vat_id, MAX_CANDIDATES - len(candidates))
        _add_candidates(rows, candidates)

    remaining = MAX_CANDIDATES - len(candidates)
    if remaining > 0:
        rows = _query_by_filters(db, normalized, remaining)
        _add_candidates(rows, candidates)

    return list(candidates.values())


def _casefold(value: str | None) -> str | None:
    if value is None:
        return None
    return value.casefold()


def compute_match_score(
    query: NormalizedQuery, company: dict[str, Any]
) -> tuple[float, str, list[str]]:
    score = 0.0
    reasons: list[str] = []
    match_type = "LOW"

    company_register_id = _normalize_register_id(company.get("register_id"))
    company_vat_id = _normalize_vat_id(company.get("vat_id"))
    company_domain = _extract_domain(company.get("website"))
    company_domain_sld = _extract_second_level_domain(company_domain)
    company_name_norm = _normalize_name(company.get("name"))
    company_city = _clean_str(company.get("city"))
    company_postal = _clean_str(company.get("postal_code"))
    company_country = normalize_country_code(company.get("country"))

    if query.register_id and company_register_id and query.register_id == company_register_id:
        score += 0.7
        reasons.append("register_id_exact_match")
        match_type = "EXACT_REGISTER_ID"

    if query.vat_id and company_vat_id and query.vat_id == company_vat_id:
        score += 0.7
        reasons.append("vat_id_exact_match")
        if match_type != "EXACT_REGISTER_ID":
            match_type = "EXACT_VAT_ID"

    if query.domain and company_domain:
        if query.domain == company_domain:
            score += 0.5
            reasons.append("domain_exact_match")
        elif (
            query.domain_sld
            and company_domain_sld
            and query.domain_sld == company_domain_sld
        ):
            score += 0.4
            reasons.append("domain_sld_match")

    if query.name_norm and company_name_norm:
        similarity = SequenceMatcher(None, query.name_norm, company_name_norm).ratio()
        if similarity >= 0.9:
            score += 0.4
            reasons.append(f"name_similarity_{similarity:.2f}")
        elif similarity >= 0.8:
            score += 0.3
            reasons.append(f"name_similarity_{similarity:.2f}")
        elif similarity >= 0.7:
            score += 0.2
            reasons.append(f"name_similarity_{similarity:.2f}")
        elif similarity >= 0.6:
            score += 0.1
            reasons.append(f"name_similarity_{similarity:.2f}")

    if query.city and company_city:
        company_city_folded = _casefold(company_city)
        query_city = _casefold(query.city)
        if query_city == company_city_folded:
            if (
                query.postal_code
                and company_postal
                and query.postal_code == company_postal
            ):
                score += 0.2
                reasons.append("same_postal_code_and_city")
            else:
                score += 0.1
                reasons.append("city_match")

    if query.country_code and company_country:
        if query.country_code == company_country:
            score += 0.05
            reasons.append("country_match")
        else:
            score -= 0.1
            reasons.append("country_mismatch")

    score = max(0.0, min(1.0, score))

    if match_type not in {"EXACT_REGISTER_ID", "EXACT_VAT_ID"}:
        if score >= 0.9:
            match_type = "HIGH"
        elif score >= 0.7:
            match_type = "MEDIUM"
        else:
            match_type = "LOW"

    return score, match_type, reasons


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@router.options("/match-company")
def match_company_options() -> Response:
    """Respond to CORS preflight requests without requiring auth."""

    return Response(status_code=200)


@router.post(
    "/match-company",
    response_model=SalesforceMatchResponse,
    dependencies=[Depends(require_salesforce_bearer_token)],
)
def match_company(
    request: SalesforceMatchRequest,
    db: Connection = Depends(get_db),
) -> SalesforceMatchResponse:
    if not _has_query_fields(request):
        raise HTTPException(
            status_code=400, detail="At least one query field must be provided"
        )

    normalized = _normalize_query_model(request)
    candidates = _collect_candidates(db, normalized)

    min_score = request.options.min_score if request.options else 0.5
    max_results = request.options.max_results if request.options else 10
    max_results = min(max_results, MAX_CANDIDATES)

    matches: list[SalesforceMatchItem] = []
    for candidate in candidates:
        score, match_type, reasons = compute_match_score(normalized, candidate)
        if score < min_score:
            continue
        matches.append(
            SalesforceMatchItem(
                source_id=candidate["source_id"],
                score=score,
                match_type=match_type,
                reasons=reasons,
                company=SalesforceMatchedCompany(**candidate),
            )
        )

    matches.sort(key=lambda item: item.score, reverse=True)
    matches = matches[:max_results]
    best_match = matches[0] if matches else None

    thresholds = SalesforceMatchThresholds()
    response = SalesforceMatchResponse(
        matches=matches,
        best_match=best_match,
        thresholds=thresholds,
    )

    context = request.context or None
    logger.info(
        "salesforce_match",
        extra={
            "source": getattr(context, "source", None) if context else None,
            "object_type": getattr(context, "object_type", None) if context else None,
            "external_id": getattr(context, "external_id", None) if context else None,
            "candidates": len(candidates),
            "best_match_source_id": best_match.source_id if best_match else None,
            "best_match_score": best_match.score if best_match else None,
        },
    )

    return response
