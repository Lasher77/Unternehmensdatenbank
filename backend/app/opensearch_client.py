from typing import Any, Iterable, Mapping

from opensearchpy import OpenSearch, helpers

from .config import get_settings
from .utils.matching_normalization import (
    normalize_city,
    normalize_company_name,
    normalize_domain,
    normalize_postal_code,
    normalize_street,
)


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
                            "street_search": {
                                "tokenizer": "standard",
                                "filter": ["lowercase", "asciifolding", "trim"],
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
                        "name_normalized": {
                            "type": "text",
                            "analyzer": "name_search",
                            "search_analyzer": "name_search",
                            "fields": {
                                "raw": {
                                    "type": "keyword",
                                    "normalizer": "keyword_lowercase",
                                }
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
                        "city_normalized": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase",
                        },
                        "postal_code": {"type": "keyword"},
                        "postal_code_normalized": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase",
                        },
                        "street": {
                            "type": "text",
                            "analyzer": "street_search",
                            "fields": {
                                "raw": {
                                    "type": "keyword",
                                    "normalizer": "keyword_lowercase",
                                }
                            },
                        },
                        "street_normalized": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase",
                        },
                        "country": {"type": "keyword"},
                        "website": {"type": "keyword", "normalizer": "keyword_lowercase"},
                        "domain_normalized": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase",
                        },
                        "email": {"type": "keyword", "normalizer": "keyword_lowercase"},
                        "phone": {"type": "keyword", "normalizer": "keyword_lowercase"},
                        "register_id": {"type": "keyword"},
                        "vat_id": {"type": "keyword"},
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
        normalized_name = normalize_company_name(item.get("name"))
        normalized_street = normalize_street(item.get("street"))
        normalized_city = normalize_city(item.get("city"))
        normalized_postal = normalize_postal_code(item.get("postal_code"))
        normalized_domain = normalize_domain(item.get("website"))
        doc = {
            "_index": "companies",
            "_id": item["source_id"],
            "_source": {
                "source_id": item.get("source_id"),
                "name": item.get("name"),
                "name_normalized": normalized_name,
                "state": item.get("state"),
                "city": item.get("city"),
                "city_normalized": normalized_city,
                "postal_code": item.get("postal_code"),
                "street": item.get("street"),
                "street_normalized": normalized_street,
                "country": item.get("country"),
                "website": item.get("website"),
                "domain_normalized": normalized_domain,
                "email": item.get("email"),
                "phone": item.get("phone"),
                "register_id": item.get("register_id"),
                "vat_id": item.get("vat_id"),
                "status": item.get("status"),
                "legal_form": item.get("legal_form"),
                "postal_code_normalized": normalized_postal,
            },
        }
        lat = item.get("lat")
        lng = item.get("lng")
        if lat is not None and lng is not None:
            doc["_source"]["location"] = {"lat": lat, "lon": lng}
        actions.append(doc)

    if actions:
        helpers.bulk(client, actions)
