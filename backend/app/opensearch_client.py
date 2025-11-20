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
        # Schemaänderungen erfordern manuelles Reindexing und ein anschließendes Löschen
        # des alten Index, um Datenverlust zu vermeiden.
        client.indices.create(
            index="companies",
            body={
                "settings": {
                    "analysis": {
                        "filter": {
                            "edge_ngram_2_20": {
                                "type": "edge_ngram",
                                "min_gram": 2,
                                "max_gram": 20,
                            }
                        },
                        "analyzer": {
                            "name_search": {
                                "tokenizer": "standard",
                                "filter": ["lowercase", "asciifolding", "trim"],
                            },
                            "name_edge": {
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "asciifolding",
                                    "trim",
                                    "edge_ngram_2_20",
                                ],
                            },
                        },
                        "normalizer": {
                            "keyword_lowercase": {
                                "type": "custom",
                                "filter": ["lowercase", "asciifolding"],
                            }
                        },
                    }
                },
                "mappings": {
                    "properties": {
                        "source_id": {"type": "keyword"},
                        "name": {
                            "type": "text",
                            "analyzer": "name_search",
                            "search_analyzer": "name_search",
                            "fields": {
                                "edge": {
                                    "type": "text",
                                    "analyzer": "name_edge",
                                },
                                "raw": {
                                    "type": "keyword",
                                    "normalizer": "keyword_lowercase",
                                },
                            },
                        },
                        "state": {"type": "keyword"},
                        "city": {
                            "type": "text",
                            "analyzer": "name_search",
                            "fields": {
                                "raw": {
                                    "type": "keyword",
                                    "normalizer": "keyword_lowercase",
                                }
                            },
                        },
                        "postal_code": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "legal_form": {"type": "keyword"},
                        "location": {"type": "geo_point"},
                    }
                },
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
