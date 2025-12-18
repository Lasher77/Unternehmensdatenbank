"""Salesforce integration endpoints."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
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


@dataclass
class HitAnalysis:
    """Lightweight analysis of a hit for confidence and reasoning."""

    strong_address_match: bool = False
    weak_address_match: bool = False
    domain_term_match: bool = False
    domain_wildcard_match: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def has_address_or_domain(self) -> bool:
        return (
            self.strong_address_match
            or self.weak_address_match
            or self.domain_term_match
            or self.domain_wildcard_match
        )


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


def _domain_fragments(normalized: NormalizedQuery) -> list[str]:
    fragments: list[str] = []
    if normalized.domain_normalized:
        fragments.append(normalized.domain_normalized)
    if normalized.email_domain_normalized and normalized.email_domain_normalized not in fragments:
        fragments.append(normalized.email_domain_normalized)
    if not fragments and normalized.website:
        fragments.append(normalized.website.lower())
    if not fragments and normalized.email:
        fragments.append(normalized.email.lower())
    return fragments


def _domain_should(normalized: NormalizedQuery) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    term_should: list[dict[str, Any]] = []
    wildcard_should: list[dict[str, Any]] = []
    normalized_fragments: list[str] = []
    wildcard_fragments: list[str] = []

    if normalized.domain_normalized:
        normalized_fragments.append(normalized.domain_normalized)
    if normalized.email_domain_normalized and normalized.email_domain_normalized not in normalized_fragments:
        normalized_fragments.append(normalized.email_domain_normalized)

    wildcard_fragments.extend(normalized_fragments)
    if normalized.website and normalized.website.lower() not in wildcard_fragments:
        wildcard_fragments.append(normalized.website.lower())
    if normalized.email and normalized.email.lower() not in wildcard_fragments:
        wildcard_fragments.append(normalized.email.lower())

    for fragment in normalized_fragments:
        term_should.append({"term": {"domain_normalized": {"value": fragment, "boost": 2.0}}})
    for fragment in wildcard_fragments:
        wildcard_should.append({"wildcard": {"website": {"value": f"*{fragment}*", "boost": 0.8}}})
        wildcard_should.append({"wildcard": {"email": {"value": f"*{fragment}", "boost": 0.6}}})

    return term_should, wildcard_should


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
    analyses: list[HitAnalysis],
    extra_reasons: list[str] | None = None,
) -> list[SalesforceMatchItem]:
    items: list[SalesforceMatchItem] = []
    extra_reasons = extra_reasons or []
    for hit, analysis in zip(hits, analyses):
        score = float(hit.get("_score", 0.0) or 0.0)
        if score < min_score:
            continue
        company = _hit_to_company(hit)
        reasons = [match_level] + extra_reasons.copy() + analysis.reasons
        status = (company.status or "").lower()
        if status == "active":
            score *= 1.05
            reasons.append("status_active_boost")
        elif status and status != "active":
            score *= 0.85
            reasons.append("status_penalty")
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


def _classify_address_match(hit: Mapping[str, Any], normalized: NormalizedQuery) -> HitAnalysis:
    source = hit.get("_source", {})
    matches_zip = False
    matches_city = False
    matches_street = False
    if normalized.postal_code:
        matches_zip = source.get("postal_code_normalized") == normalized.postal_code
    if normalized.city_normalized:
        matches_city = source.get("city_normalized") == normalized.city_normalized
    if normalized.street_normalized:
        matches_street = source.get("street_normalized") == normalized.street_normalized

    strong_address_match = matches_zip or (matches_city and matches_street)
    weak_address_match = not strong_address_match and (matches_city or matches_street)

    reasons: list[str] = []
    if matches_zip:
        reasons.append("address_match_zip")
    if matches_city:
        reasons.append("address_match_city")
    if matches_street:
        reasons.append("address_match_street")
    if strong_address_match:
        reasons.append("address_match_strong")
    elif weak_address_match:
        reasons.append("address_match_weak")

    return HitAnalysis(
        strong_address_match=strong_address_match,
        weak_address_match=weak_address_match,
        reasons=reasons,
    )


def _analyze_hit_domain(hit: Mapping[str, Any], domain_fragments: list[str]) -> tuple[bool, bool]:
    if not domain_fragments:
        return False, False
    source = hit.get("_source", {})
    domain_normalized = (source.get("domain_normalized") or "").lower()
    website = (source.get("website") or "").lower()
    email = (source.get("email") or "").lower()

    term_match = bool(domain_normalized and domain_normalized in domain_fragments)
    wildcard_match = False
    for fragment in domain_fragments:
        if fragment in website or email.endswith(fragment):
            wildcard_match = True
            break
    return term_match, wildcard_match


def _analyze_hit(hit: Mapping[str, Any], normalized: NormalizedQuery, domain_fragments: list[str]) -> HitAnalysis:
    analysis = _classify_address_match(hit, normalized)
    term_match, wildcard_match = _analyze_hit_domain(hit, domain_fragments)
    if term_match:
        analysis.domain_term_match = True
        analysis.reasons.append("domain_term_match")
    if wildcard_match:
        analysis.domain_wildcard_match = True
        analysis.reasons.append("domain_wildcard_match")
    return analysis


def _rerank_hits_by_address(hits: list[Mapping[str, Any]], normalized: NormalizedQuery) -> list[Mapping[str, Any]]:
    def _priority(hit: Mapping[str, Any]) -> tuple[int, int, float]:
        analysis = _classify_address_match(hit, normalized)
        strong = 1 if analysis.strong_address_match else 0
        weak = 1 if analysis.weak_address_match else 0
        score = float(hit.get("_score", 0.0) or 0.0)
        return (strong, weak, score)

    return sorted(hits, key=_priority, reverse=True)


def _stage_domain_match(
    client: OpenSearch, normalized: NormalizedQuery, size: int
) -> tuple[list[Mapping[str, Any]], str | None]:
    term_should, wildcard_should = _domain_should(normalized)
    if not term_should and not wildcard_should:
        return [], None
    filters = _country_filter(normalized)

    if term_should:
        base_query = {
            "size": size,
            "query": {
                "bool": {
                    "should": term_should,
                    "filter": filters,
                    "minimum_should_match": 1,
                }
            },
        }
        hits = _run_search(client, base_query)
        hits_with_domain = [
            hit for hit in hits if hit.get("_source", {}).get("domain_normalized")
        ]
        if hits_with_domain:
            return hits_with_domain, "DOMAIN_EXACT"

    if wildcard_should:
        must = [{"bool": {"should": wildcard_should, "minimum_should_match": 1}}]
        should = wildcard_should + _address_should(normalized)
        if normalized.name_normalized:
            should.append(_name_query(normalized, fuzziness=None))

        refined_query = {
            "size": size,
            "query": {
                "bool": {
                    "must": must,
                    "should": should,
                    "filter": filters,
                    "minimum_should_match": 1,
                }
            },
        }
        hits = _run_search(client, refined_query)
        if not hits and should:
            refined_query["query"]["bool"]["minimum_should_match"] = 0
            hits = _run_search(client, refined_query)
        if hits:
            return hits, "DOMAIN_FUZZY"

    return [], None


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


_GENERIC_NAME_TOKENS = {
    "agentur",
    "marketing",
    "service",
    "services",
    "consulting",
    "solutions",
    "media",
    "management",
    "handel",
    "vertrieb",
    "logistik",
    "systems",
    "systeme",
    "digital",
    "it",
    "group",
    "holding",
    "holdinggesellschaft",
    "firma",
    "company",
    "consult",
    "design",
    "agentur",
    "creative",
    "produktion",
    "production",
    "gmbh",
    "ag",
    "ug",
    "kg",
    "mbh",
}


def _generic_name_penalty(normalized_name: str | None) -> float:
    if not normalized_name:
        return 0.0
    tokens = [token for token in normalized_name.split() if token]
    if not tokens:
        return 0.0
    generic_count = sum(1 for token in tokens if token in _GENERIC_NAME_TOKENS)
    ratio = generic_count / len(tokens)
    if ratio >= 0.6 or (len(tokens) <= 3 and generic_count >= len(tokens) - 1):
        return -0.12
    if ratio >= 0.4:
        return -0.07
    return 0.0


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


def _has_address_or_domain_signals(normalized: NormalizedQuery) -> bool:
    return any(
        [
            normalized.postal_code,
            normalized.city_normalized,
            normalized.street_normalized,
            normalized.domain_normalized,
            normalized.email_domain_normalized,
            normalized.website,
            normalized.email,
        ]
    )


def _stage_name_strict(
    client: OpenSearch, normalized: NormalizedQuery, size: int
) -> tuple[list[Mapping[str, Any]], bool]:
    if not normalized.name_normalized:
        return [], False
    filters = _country_filter(normalized)
    address_should = _address_should(normalized)
    domain_term_should, domain_wildcard_should = _domain_should(normalized)
    should = address_should + domain_term_should + domain_wildcard_should
    enforce_signals = _has_address_or_domain_signals(normalized) and bool(should)
    minimum_should = 1 if enforce_signals else 0
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
    hits = _run_search(client, query)
    if not hits and enforce_signals:
        query["query"]["bool"]["minimum_should_match"] = 0
        hits = _run_search(client, query)
        return hits, True
    return hits, False


def _stage_name_fuzzy(
    client: OpenSearch, normalized: NormalizedQuery, size: int
) -> tuple[list[Mapping[str, Any]], bool]:
    if not normalized.name_normalized:
        return [], False
    filters = _country_filter(normalized)
    address_should = _address_should(normalized)
    domain_term_should, domain_wildcard_should = _domain_should(normalized)
    should = address_should + domain_term_should + domain_wildcard_should
    enforce_signals = _has_address_or_domain_signals(normalized) and bool(should)
    minimum_should = 1 if enforce_signals else 0
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
    hits = _run_search(client, query)
    if not hits and enforce_signals:
        query["query"]["bool"]["minimum_should_match"] = 0
        hits = _run_search(client, query)
        return hits, True
    return hits, False


def _compute_confidence(
    level: str,
    hits: list[Mapping[str, Any]],
    analyses: list[HitAnalysis],
    generic_penalty: float,
) -> tuple[float, list[str]]:
    base = {
        "DOMAIN_EXACT": 0.95,
        "DOMAIN_FUZZY": 0.85,
        "NAME_ADDRESS_STRICT": 0.9,
        "NAME_STRICT": 0.8,
        "NAME_FUZZY_WITH_ADDRESS": 0.7,
        "NAME_FUZZY_ONLY": 0.55,
        "NO_MATCH": 0.0,
    }.get(level, 0.5)

    confidence = base
    reasons: list[str] = []

    if len(hits) > 1:
        top = float(hits[0].get("_score", 0.0) or 0.0)
        second = float(hits[1].get("_score", 0.0) or 0.0)
        if top > 0:
            delta = max(0.0, top - second) / top
            confidence += min(0.1, delta * 0.1)

    if analyses:
        top_analysis = analyses[0]
        if top_analysis.strong_address_match:
            confidence += 0.05
            if level in ("NAME_STRICT", "NAME_ADDRESS_STRICT"):
                confidence = min(confidence, 0.85)
            elif level.startswith("NAME_FUZZY"):
                confidence = min(confidence, 0.75)
        elif top_analysis.weak_address_match:
            confidence += 0.02
            if level.startswith("NAME"):
                confidence = min(confidence, 0.8)

        if level in ("NAME_STRICT", "NAME_FUZZY_WITH_ADDRESS", "NAME_FUZZY_ONLY", "NAME_ADDRESS_STRICT"):
            if not top_analysis.has_address_or_domain:
                cap = 0.75 if level == "NAME_STRICT" else 0.65
                confidence = min(confidence, cap)
                reasons.append("name_only_confidence_cap")

        if level == "NAME_FUZZY_ONLY":
            confidence = min(confidence, 0.65)

    if generic_penalty < 0:
        confidence = max(0.0, confidence + generic_penalty)
        reasons.append("generic_name_penalty")

    return max(0.0, min(1.0, confidence)), reasons


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
    generic_penalty = _generic_name_penalty(normalized.name_normalized)
    domain_fragments = _domain_fragments(normalized)
    confidence_reasons: list[str] = []
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
            name_hits, _ = _stage_name_strict(client, normalized, max_results)
            if name_hits:
                hits = name_hits
                match_level = "NAME_STRICT"
            else:
                fuzzy_hits, _ = _stage_name_fuzzy(client, normalized, max_results)
                if fuzzy_hits:
                    hits = _rerank_hits_by_address(fuzzy_hits, normalized)
                    address_match = any(_has_address_match(hit, normalized) for hit in hits)
                    match_level = "NAME_FUZZY_WITH_ADDRESS" if address_match else "NAME_FUZZY_ONLY"

    analyses = [_analyze_hit(hit, normalized, domain_fragments) for hit in hits]

    confidence, confidence_reason_flags = _compute_confidence(
        match_level if hits else "NO_MATCH", hits, analyses, generic_penalty
    )
    confidence_reasons.extend(confidence_reason_flags)

    matches = _hits_to_match_items(hits, match_level, min_score, analyses, extra_reasons=confidence_reasons)
    matches.sort(key=lambda m: m.score, reverse=True)
    matches = matches[:max_results]
    best_match = matches[0] if matches else None

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
