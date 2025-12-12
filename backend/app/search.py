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
            "state": {"terms": {"field": "state"}},
            "city": {"terms": {"field": "city.raw"}},
            "status": {"terms": {"field": "status"}},
            "legal_form": {"terms": {"field": "legal_form"}},
        },
    }

    filters: List[Dict[str, Any]] = []

    if q := params.get("query"):
        body["query"] = {"simple_query_string": {"query": q}}

    field_mapping = {
        "state": "state",
        "city": "city.raw",
        "postal_code": "postal_code",
        "wz": "wz",
        "status": "status",
        "legal_form": "legal_form",
    }

    for field, target in field_mapping.items():
        if value := params.get(field):
            filters.append({"term": {target: value}})

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
            "status": h.get("_source", {}).get("status"),
        }
        for h in hits.get("hits", [])
    ]

    facets: Dict[str, List[Dict[str, Any]]] = {}
    for facet, agg in response.get("aggregations", {}).items():
        facets[facet] = [
            {"value": bucket["key"], "count": bucket["doc_count"]}
            for bucket in agg.get("buckets", [])
        ]

    return {"total": total, "results": results, "facets": facets}
