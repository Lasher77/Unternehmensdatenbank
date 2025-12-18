import os
from typing import Any, Iterable, List

from fastapi.testclient import TestClient

# Ensure the token is available before the app and auth dependency are imported
os.environ.setdefault("SALESFORCE_MATCH_API_TOKEN", "test-token")

from backend.app.deps import get_os_client  # noqa: E402
from backend.app.dependencies.auth import require_salesforce_bearer_token  # noqa: E402
from backend.app.main import app  # noqa: E402


class FakeOpenSearch:
    """Minimal stub mimicking the parts of ``OpenSearch`` used in tests."""

    def __init__(self, responses: Iterable[List[dict[str, Any]]]):
        self._responses = list(responses)

    def search(self, index: str, body: dict[str, Any]):  # pragma: no cover - simple stub
        try:
            hits = self._responses.pop(0)
        except IndexError:
            hits = []
        return {"hits": {"hits": hits}}


def _build_test_client(os_hits: Iterable[List[dict[str, Any]]]) -> TestClient:
    app.router.on_startup.clear()
    app.dependency_overrides[get_os_client] = lambda: FakeOpenSearch(os_hits)
    app.dependency_overrides[require_salesforce_bearer_token] = (
        lambda: {"integration": "salesforce"}
    )
    return TestClient(app)


def test_match_company_returns_domain_result():
    client = _build_test_client(
        [
            [
                {
                    "_score": 1.2,
                    "_source": {
                        "source_id": "123",
                        "name": "Mueritz GmbH",
                        "email": "contact@example.com",
                        "street": "Hauptstrasse 1",
                        "postal_code": "10115",
                        "city": "Berlin",
                        "country": "DE",
                        "website": "https://mueritz.de",
                        "domain_normalized": "mueritz.de",
                        "phone": "+49 30 123456",
                        "revenue": 1_000_000,
                        "register_id": "HRB 123",
                        "vat_id": "DE123456789",
                        "status": "active",
                    },
                }
            ]
        ]
    )

    response = client.post(
        "/api/salesforce/match-company",
        headers={"Authorization": "Bearer test-token"},
        json={
            "query": {
                "name": "Müritz",
                "website": "mueritz.de",
                "city": "Berlin",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["match_level"] == "DOMAIN_EXACT"
    assert payload["matches"][0]["company"]["source_id"] == "123"
    assert payload["best_match"]["company"]["name"] == "Mueritz GmbH"
    assert "domain_term_match" in payload["matches"][0]["reasons"]



def test_match_company_prefers_address_fuzzy_matches():
    fuzzy_hits: list[dict[str, Any]] = [
        {
            "_score": 0.9,
            "_source": {
                "source_id": "abc",
                "name": "Mueller Services",
                "street": "Hauptstrasse 5",
                "street_normalized": "hauptstrasse 5",
                "postal_code": "80331",
                "postal_code_normalized": "80331",
                "city": "Muenchen",
                "city_normalized": "munchen",
                "country": "DE",
            },
        },
        {
            "_score": 0.65,
            "_source": {
                "source_id": "def",
                "name": "Muller Service GmbH",
                "street": "Hauptstrasse 50",
                "street_normalized": "hauptstrasse 50",
                "postal_code": "80339",
                "postal_code_normalized": "80339",
                "city": "Muenchen",
                "city_normalized": "munchen",
                "country": "DE",
            },
        },
    ]

    client = _build_test_client([[], [], [], fuzzy_hits])

    response = client.post(
        "/api/salesforce/match-company",
        headers={"Authorization": "Bearer test-token"},
        json={
            "query": {
                "name": "Müller Service",
                "street": "Hauptstraße 5",
                "postal_code": "80331",
                "city": "München",
                "country": "de",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["match_level"] == "NAME_FUZZY_WITH_ADDRESS"
    assert payload["matches"][0]["company"]["source_id"] == "abc"
    assert payload["matches"][1]["company"]["source_id"] == "def"
    assert "address_match_strong" in payload["matches"][0]["reasons"]
    assert "address_match_city" in payload["matches"][1]["reasons"]

    app.dependency_overrides.clear()


def test_match_company_uses_email_domain_when_no_website():
    client = _build_test_client(
        [
            [
                {
                    "_score": 1.4,
                    "_source": {
                        "source_id": "email-1",
                        "name": "Acme Widgets GmbH",
                        "email": "sales@acme-widgets.example",
                        "domain_normalized": "acme-widgets.example",
                        "country": "DE",
                        "website": None,
                        "status": "active",
                    },
                }
            ]
        ]
    )

    response = client.post(
        "/api/salesforce/match-company",
        headers={"Authorization": "Bearer test-token"},
        json={
            "query": {
                "name": "Acme Widgets",
                "email": "sales@acme-widgets.example",
                "country": "DE",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["match_level"] == "DOMAIN_EXACT"
    assert payload["best_match"]["company"]["source_id"] == "email-1"


def test_match_company_handles_name_only_fuzzy_request():
    fuzzy_hits: list[dict[str, Any]] = [
        {
            "_score": 0.8,
            "_source": {
                "source_id": "solo-name",
                "name": "Globex Corporation",
                "country": "DE",
            },
        }
    ]

    client = _build_test_client([[], fuzzy_hits])

    response = client.post(
        "/api/salesforce/match-company",
        headers={"Authorization": "Bearer test-token"},
        json={"query": {"name": "Globex Corp", "country": "DE"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["match_level"] == "NAME_FUZZY_ONLY"
    assert payload["best_match"]["company"]["source_id"] == "solo-name"


def test_name_strict_requires_address_when_available():
    name_only_hit: list[dict[str, Any]] = [
        {
            "_score": 1.1,
            "_source": {
                "source_id": "lonely",
                "name": "Testfirma GmbH",
                "country": "DE",
            },
        }
    ]

    client = _build_test_client([[], [], name_only_hit])

    response = client.post(
        "/api/salesforce/match-company",
        headers={"Authorization": "Bearer test-token"},
        json={
            "query": {
                "name": "Testfirma GmbH",
                "street": "Falsche Strasse 1",
                "postal_code": "99999",
                "city": "Nowhere",
                "country": "DE",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["match_level"] == "NAME_STRICT"
    assert payload["result"]["confidence"] <= 0.75
    assert "name_only_confidence_cap" in payload["matches"][0]["reasons"]


def test_domain_fuzzy_level_and_reasons():
    wildcard_hits: list[dict[str, Any]] = [
        {
            "_score": 0.9,
            "_source": {
                "source_id": "wild-1",
                "name": "Example Org",
                "website": "https://example.org/home",
                "email": "team@example.org",
                "country": "DE",
            },
        }
    ]

    client = _build_test_client(
        [
            [
                {
                    "_score": 1.0,
                    "_source": {
                        "source_id": "no-domain",
                        "name": "Example Org",
                        "website": "https://example.org",
                        "country": "DE",
                    },
                }
            ],
            wildcard_hits,
        ]
    )

    response = client.post(
        "/api/salesforce/match-company",
        headers={"Authorization": "Bearer test-token"},
        json={
            "query": {
                "name": "Example Org",
                "website": "example.org",
                "country": "DE",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["match_level"] == "DOMAIN_FUZZY"
    assert "domain_wildcard_match" in payload["matches"][0]["reasons"]
    assert payload["best_match"]["company"]["source_id"] == "wild-1"


def test_generic_name_penalty_applies():
    name_hits: list[dict[str, Any]] = [
        {
            "_score": 1.0,
            "_source": {
                "source_id": "generic",
                "name": "Marketing Service GmbH",
                "country": "DE",
            },
        }
    ]

    client = _build_test_client([name_hits])

    response = client.post(
        "/api/salesforce/match-company",
        headers={"Authorization": "Bearer test-token"},
        json={"query": {"name": "Marketing Service GmbH", "country": "DE"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["match_level"] == "NAME_STRICT"
    assert payload["result"]["confidence"] < 0.7
    assert "generic_name_penalty" in payload["matches"][0]["reasons"]
