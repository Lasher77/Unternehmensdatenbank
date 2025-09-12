from typing import Any, Dict, List

from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError


INDEX = "companies"


def _build_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build the OpenSearch query body from API parameters."""

    page = max(params.get("page", 1), 1)
    per_page = params.get("per_page", 20)

    body: Dict[str, Any] = {
        "from": (page - 1) * per_page,
        "size": per_page,
        "query": {"match_all": {}},
        "aggs": {
            "state": {"terms": {"field": "state.keyword"}},
            "city": {"terms": {"field": "city.keyword"}},
            "status": {"terms": {"field": "status.keyword"}},
            "legal_form": {"terms": {"field": "legal_form.keyword"}},
        },
    }

    filters: List[Dict[str, Any]] = []

    if q := params.get("query"):
        body["query"] = {"simple_query_string": {"query": q}}

    for field in ["state", "city", "postal_code", "wz", "status", "legal_form"]:
        if value := params.get(field):
            filters.append({"term": {f"{field}.keyword": value}})

    if (
        params.get("lat") is not None
        and params.get("lng") is not None
        and params.get("radius_km")
    ):
        filters.append(
            {
                "geo_distance": {
                    "distance": f"{params['radius_km']}km",
                    "location": {"lat": params["lat"], "lon": params["lng"]},
                }
            }
        )

    if filters:
        body["query"] = {"bool": {"must": body["query"], "filter": filters}}

    if sort := params.get("sort"):
        body["sort"] = [sort]

    return body


def search_companies(client: OpenSearch, query: Dict[str, Any]) -> Dict[str, Any]:
    """Search companies in OpenSearch and return a structured result."""

    body = _build_query(query)
    try:
        response = client.search(index=INDEX, body=body)
    except NotFoundError:
        raise

    hits = response.get("hits", {})
    total = hits.get("total", {}).get("value", 0)
    results = [
        {
            "source_id": h.get("_source", {}).get("source_id", ""),
            "name": h.get("_source", {}).get("name"),
        }
        for h in hits.get("hits", [])
    ]

    facets: Dict[str, Dict[str, int]] = {}
    for facet, agg in response.get("aggregations", {}).items():
        facets[facet] = {bucket["key"]: bucket["doc_count"] for bucket in agg.get("buckets", [])}

    return {"total": total, "results": results, "facets": facets}
