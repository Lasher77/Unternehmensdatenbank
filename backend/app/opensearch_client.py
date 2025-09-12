from typing import Iterable, Mapping, Any

from opensearchpy import OpenSearch, helpers

from .config import get_settings


settings = get_settings()


def get_opensearch() -> OpenSearch:
    return OpenSearch(
        hosts=[
            {
                "host": settings.opensearch_host,
                "port": settings.opensearch_port,
                "scheme": "https" if settings.opensearch_use_ssl else "http",
            }
        ],
        http_compress=True,
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=False,
    )


def ensure_companies_index(client: OpenSearch) -> None:
    """Ensure that the ``companies`` index exists with the proper mappings."""
    if not client.indices.exists(index="companies"):
        client.indices.create(
            index="companies",
            body={
                "mappings": {
                    "properties": {
                        "source_id": {"type": "keyword"},
                        "name": {"type": "text"},
                        "state": {"type": "keyword"},
                        "city": {"type": "keyword"},
                        "postal_code": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "legal_form": {"type": "keyword"},
                        "location": {"type": "geo_point"},
                    }
                }
            },
        )


def index_companies(client: OpenSearch, companies: Iterable[Mapping[str, Any]]) -> None:
    """Index the given ``companies`` into the ``companies`` OpenSearch index."""
    actions = []
    for item in companies:
        doc = {
            "_index": "companies",
            "_id": item["source_id"],
            "_source": {
                "source_id": item.get("source_id"),
                "name": item.get("name"),
                "state": item.get("state"),
                "city": item.get("city"),
                "postal_code": item.get("postal_code"),
                "status": item.get("status"),
                "legal_form": item.get("legal_form"),
            },
        }
        lat = item.get("lat")
        lng = item.get("lng")
        if lat is not None and lng is not None:
            doc["_source"]["location"] = {"lat": lat, "lon": lng}
        actions.append(doc)

    if actions:
        helpers.bulk(client, actions)
