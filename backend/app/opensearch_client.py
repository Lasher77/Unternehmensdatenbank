from opensearchpy import OpenSearch

from .config import get_settings


settings = get_settings()


def get_opensearch() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        http_compress=True,
    )
