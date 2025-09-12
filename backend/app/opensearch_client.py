from opensearchpy import OpenSearch

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
