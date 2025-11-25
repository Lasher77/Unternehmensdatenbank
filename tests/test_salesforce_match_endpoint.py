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

    client = _build_test_client([[], [], fuzzy_hits])

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
