from opensearchpy import OpenSearch

from .config import get_settings


settings = get_settings()


def get_opensearch() -> OpenSearch:
    return OpenSearch(
        hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
        http_compress=True,
        use_ssl=settings.opensearch_use_ssl,
        verify_certs=False,
        basic_auth=(settings.opensearch_user, settings.opensearch_password),
    )
