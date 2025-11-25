"""Salesforce integration endpoints."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from opensearchpy import OpenSearch

from ..deps import get_os_client
from ..dependencies.auth import require_salesforce_bearer_token
from ..schemas.salesforce_match import (
    SalesforceMatchItem,
    SalesforceMatchOptions,
    SalesforceMatchRequest,
    SalesforceMatchResponse,
    SalesforceMatchedCompany,
    SalesforceMatchResult,
    SalesforceMatchThresholds,
)
from ..utils.matching_normalization import (
    normalize_city,
    normalize_company_name,
    normalize_domain,
    normalize_postal_code,
    normalize_street,
)

router = APIRouter(prefix="/api/salesforce", tags=["salesforce"])

logger = logging.getLogger(__name__)

MAX_RESULTS = 10
INDEX = "companies"


@dataclass
class NormalizedQuery:
    """Normalized values from a ``SalesforceMatchQuery`` for matching/scoring."""

    name: str | None = None
    name_normalized: str | None = None
    street: str | None = None
    street_normalized: str | None = None
    postal_code: str | None = None
    city: str | None = None
    city_normalized: str | None = None
    country: str | None = None
    domain_normalized: str | None = None
    website: str | None = None
    email: str | None = None
    email_domain_normalized: str | None = None


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_email(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    cleaned = value.strip().lower()
    if not cleaned:
        return None, None
    if "@" not in cleaned:
        return cleaned, None
    _, domain = cleaned.rsplit("@", 1)
    return cleaned, normalize_domain(domain)


def _normalize_query_model(match_request: SalesforceMatchRequest) -> NormalizedQuery:
    q = match_request.query
    country_clean = _clean_str(q.country)
    email_clean, email_domain = _normalize_email(getattr(q, "email", None))
    return NormalizedQuery(
        name=_clean_str(q.name),
        name_normalized=normalize_company_name(q.name),
        street=_clean_str(q.street),
        street_normalized=normalize_street(q.street),
        postal_code=normalize_postal_code(_clean_str(q.postal_code)),
        city=_clean_str(q.city),
        city_normalized=normalize_city(q.city),
        country=country_clean.upper() if country_clean else None,
        domain_normalized=normalize_domain(q.website),
        website=_clean_str(q.website),
        email=email_clean,
        email_domain_normalized=email_domain,
    )


def _has_query_fields(match_request: SalesforceMatchRequest) -> bool:
    for value in match_request.query.model_dump().values():
        if isinstance(value, str) and value.strip():
            return True
        if value not in (None, [], {}):
            return True
    return False


def _address_should(normalized: NormalizedQuery) -> list[dict[str, Any]]:
    should: list[dict[str, Any]] = []
    if normalized.postal_code:
        should.append(
            {"term": {"postal_code_normalized": {"value": normalized.postal_code, "boost": 3}}}
        )
    if normalized.city_normalized:
        should.append(
            {"term": {"city_normalized": {"value": normalized.city_normalized, "boost": 2}}}
        )
    if normalized.street_normalized:
        should.append(
            {"term": {"street_normalized": {"value": normalized.street_normalized, "boost": 1.5}}}
        )
    return should


def _domain_should(normalized: NormalizedQuery) -> list[dict[str, Any]]:
    should: list[dict[str, Any]] = []
    fragments: list[str] = []

    if normalized.domain_normalized:
        fragments.append(normalized.domain_normalized)
    if (
        normalized.email_domain_normalized
        and normalized.email_domain_normalized not in fragments
    ):
        fragments.append(normalized.email_domain_normalized)

    website_fragment = normalized.website.lower() if normalized.website else None
    email_fragment = normalized.email

    for fragment in fragments:
        should.append({"term": {"domain_normalized": fragment}})
        should.append(
            {"wildcard": {"website": {"value": f"*{fragment}*", "boost": 0.8}}}
        )
        should.append({"wildcard": {"email": {"value": f"*{fragment}", "boost": 0.6}}})

    if website_fragment and not fragments:
        should.append(
            {"wildcard": {"website": {"value": f"*{website_fragment}*", "boost": 1.0}}}
        )
    if email_fragment and not fragments:
        should.append({"wildcard": {"email": {"value": f"*{email_fragment}", "boost": 0.6}}})

    return should


def _country_filter(normalized: NormalizedQuery) -> list[dict[str, Any]]:
    if not normalized.country:
        return []
    return [{"term": {"country": normalized.country}}]


def _run_search(client: OpenSearch, body: dict[str, Any]) -> list[Mapping[str, Any]]:
    response = client.search(index=INDEX, body=body)
    return response.get("hits", {}).get("hits", [])


def _hit_to_company(hit: Mapping[str, Any]) -> SalesforceMatchedCompany:
    source = hit.get("_source", {})
    return SalesforceMatchedCompany(
        source_id=str(source.get("source_id")),
        name=source.get("name"),
        email=source.get("email"),
        street=source.get("street"),
        postal_code=source.get("postal_code"),
        city=source.get("city"),
        country=source.get("country"),
        website=source.get("website"),
        phone=source.get("phone"),
        revenue=source.get("revenue"),
        register_id=source.get("register_id"),
        vat_id=source.get("vat_id"),
        status=source.get("status"),
    )


def _hits_to_match_items(
    hits: list[Mapping[str, Any]],
    match_level: str,
    min_score: float,
    address_match_source_id: str | None = None,
) -> list[SalesforceMatchItem]:
    items: list[SalesforceMatchItem] = []
    for hit in hits:
        score = float(hit.get("_score", 0.0) or 0.0)
        if score < min_score:
            continue
        company = _hit_to_company(hit)
        reasons = [match_level]
        status = (company.status or "").lower()
        if status == "active":
            score *= 1.05
            reasons.append("status_active_boost")
        elif status and status != "active":
            score *= 0.85
            reasons.append("status_penalty")
        if address_match_source_id and str(company.source_id) == str(address_match_source_id):
            reasons.append("address_match")
        items.append(
            SalesforceMatchItem(
                source_id=company.source_id,
                score=score,
                match_type=match_level,
                company=company,
                reasons=reasons,
            )
        )
    return items


def _has_address_match(hit: Mapping[str, Any], normalized: NormalizedQuery) -> bool:
    source = hit.get("_source", {})
    if normalized.postal_code and source.get("postal_code_normalized") == normalized.postal_code:
        return True
    if normalized.city_normalized and source.get("city_normalized") == normalized.city_normalized:
        return True
    if normalized.street_normalized and source.get("street_normalized") == normalized.street_normalized:
        return True
    return False


def _stage_domain_match(
    client: OpenSearch, normalized: NormalizedQuery, size: int
) -> tuple[list[Mapping[str, Any]], str | None]:
    domain_should = _domain_should(normalized)
    if not domain_should:
        return [], None
    filters = _country_filter(normalized)

    base_query = {
        "size": size,
        "query": {
            "bool": {
                "should": domain_should,
                "filter": filters,
                "minimum_should_match": 1,
            }
        },
    }
    hits = _run_search(client, base_query)
    if len(hits) <= 1:
        return hits, "DOMAIN_EXACT" if hits else None

    must: list[dict[str, Any]] = [
        {"bool": {"should": domain_should, "minimum_should_match": 1}},
    ]
    if normalized.name_normalized:
        must.append(_name_query(normalized, fuzziness=None))
    should = domain_should + _address_should(normalized)
    refined_query = {
        "size": size,
        "query": {
            "bool": {
                "must": must,
                "should": should,
                "filter": filters,
                "minimum_should_match": 1 if should else 0,
            }
        },
    }
    refined_hits = _run_search(client, refined_query)
    if not refined_hits and should:
        refined_query["query"]["bool"]["minimum_should_match"] = 0
        refined_hits = _run_search(client, refined_query)
    return refined_hits, "DOMAIN_EXACT" if refined_hits else None


def _name_query(
    normalized: NormalizedQuery, fuzziness: int | str | None = 0, prefix_length: int | None = None
) -> dict[str, Any]:
    match: dict[str, Any] = {
        "query": normalized.name_normalized,
        "fields": ["name_normalized", "name", "name.edge"],
        "operator": "and",
    }
    if fuzziness is not None:
        match["fuzziness"] = fuzziness
    if prefix_length is not None:
        match["prefix_length"] = prefix_length
    return {"multi_match": match}


def _stage_name_address(
    client: OpenSearch, normalized: NormalizedQuery, size: int
) -> list[Mapping[str, Any]]:
    if not normalized.name_normalized:
        return []
    filters = _country_filter(normalized)
    address_should = _address_should(normalized)
    if not address_should:
        return []
    query = {
        "size": size,
        "query": {
            "bool": {
                "must": [_name_query(normalized, fuzziness=0)],
                "should": address_should,
                "filter": filters,
                "minimum_should_match": 1 if address_should else 0,
            }
        },
    }
    return _run_search(client, query)


def _stage_name_strict(client: OpenSearch, normalized: NormalizedQuery, size: int) -> list[Mapping[str, Any]]:
    if not normalized.name_normalized:
        return []
    filters = _country_filter(normalized)
    address_should = _address_should(normalized)
    should = address_should + _domain_should(normalized)
    # Address/domain matches should improve the score but must not block name-only
    # matches when the address information is incomplete or differs slightly from
    # the indexed data. Therefore we keep them as optional ``should`` clauses.
    minimum_should = 0
    query = {
        "size": size,
        "query": {
            "bool": {
                "must": [_name_query(normalized, fuzziness=0)],
                "should": should,
                "filter": filters,
                "minimum_should_match": minimum_should,
            }
        },
    }
    return _run_search(client, query)


def _stage_name_fuzzy(
    client: OpenSearch, normalized: NormalizedQuery, size: int
) -> list[Mapping[str, Any]]:
    if not normalized.name_normalized:
        return []
    filters = _country_filter(normalized)
    address_should = _address_should(normalized)
    should = address_should + _domain_should(normalized)
    # Keep address/domain signals optional to avoid suppressing good name matches
    # when the address does not align perfectly with indexed data.
    minimum_should = 0
    query = {
        "size": size,
        "query": {
            "bool": {
                "must": [_name_query(normalized, fuzziness="AUTO", prefix_length=2)],
                "should": should,
                "filter": filters,
                "minimum_should_match": minimum_should,
            }
        },
    }
    return _run_search(client, query)


def _compute_confidence(
    level: str, hits: list[Mapping[str, Any]], address_match: bool
) -> float:
    base = {
        "DOMAIN_EXACT": 0.95,
        "NAME_ADDRESS_STRICT": 0.9,
        "NAME_STRICT": 0.8,
        "NAME_FUZZY_WITH_ADDRESS": 0.7,
        "NAME_FUZZY_ONLY": 0.55,
        "NO_MATCH": 0.0,
    }.get(level, 0.5)

    confidence = base
    if len(hits) > 1:
        top = float(hits[0].get("_score", 0.0) or 0.0)
        second = float(hits[1].get("_score", 0.0) or 0.0)
        if top > 0:
            delta = max(0.0, top - second) / top
            confidence += min(0.1, delta * 0.1)
    if address_match:
        confidence += 0.05
    return max(0.0, min(1.0, confidence))


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
    client: OpenSearch = Depends(get_os_client),
) -> SalesforceMatchResponse:
    if not _has_query_fields(request):
        raise HTTPException(
            status_code=400, detail="At least one query field must be provided"
        )

    normalized = _normalize_query_model(request)
    options = request.options or SalesforceMatchOptions()
    max_results = min(options.max_results, MAX_RESULTS)
    min_score = options.min_score

    match_level = "NO_MATCH"
    address_match = False
    hits: list[Mapping[str, Any]] = []

    domain_hits, domain_level = _stage_domain_match(client, normalized, max_results)
    if domain_hits:
        hits = domain_hits
        match_level = domain_level or "DOMAIN_EXACT"
    else:
        name_address_hits = _stage_name_address(client, normalized, max_results)
        if name_address_hits:
            hits = name_address_hits
            match_level = "NAME_ADDRESS_STRICT"
        else:
            name_hits = _stage_name_strict(client, normalized, max_results)
            if name_hits:
                hits = name_hits
                match_level = "NAME_STRICT"
            else:
                fuzzy_hits = _stage_name_fuzzy(client, normalized, max_results)
                if fuzzy_hits:
                    hits = fuzzy_hits
                    for hit in hits:
                        if _has_address_match(hit, normalized):
                            address_match = True
                            # move address matched hit to front
                            hits = [hit] + [h for h in hits if h is not hit]
                            break
                    match_level = "NAME_FUZZY_WITH_ADDRESS" if address_match else "NAME_FUZZY_ONLY"

    matches = _hits_to_match_items(
        hits,
        match_level,
        min_score,
        address_match_source_id=hits[0].get("_source", {}).get("source_id") if address_match and hits else None,
    )
    matches.sort(key=lambda m: m.score, reverse=True)
    matches = matches[:max_results]
    best_match = matches[0] if matches else None

    confidence = _compute_confidence(match_level if matches else "NO_MATCH", hits, address_match)
    result = SalesforceMatchResult(
        company=best_match.company if best_match else None,
        match_level=match_level if matches else "NO_MATCH",
        confidence=confidence,
    )

    thresholds = SalesforceMatchThresholds()
    response = SalesforceMatchResponse(
        matches=matches,
        best_match=best_match,
        result=result,
        thresholds=thresholds,
    )

    context = request.context or None
    logger.info(
        "salesforce_match",
        extra={
            "source": getattr(context, "source", None) if context else None,
            "object_type": getattr(context, "object_type", None) if context else None,
            "external_id": getattr(context, "external_id", None) if context else None,
            "best_match_source_id": best_match.source_id if best_match else None,
            "best_match_score": best_match.score if best_match else None,
            "match_level": match_level,
        },
    )

    return response
