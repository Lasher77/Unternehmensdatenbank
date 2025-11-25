import sys
from pathlib import Path

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.deps import get_os_client
from backend.app.dependencies.auth import require_salesforce_bearer_token
from backend.app.main import app


def test_salesforce_match_company_options_does_not_require_auth() -> None:
    client = TestClient(app)

    response = client.options("/api/salesforce/match-company")

    assert response.status_code == 200


class RecordingOSClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def search(self, index: str, body: dict) -> dict:
        self.calls.append({"index": index, "body": body})
        return {"hits": {"hits": []}}


def test_match_company_applies_country_filter() -> None:
    client = RecordingOSClient()
    app.dependency_overrides[get_os_client] = lambda: client
    app.dependency_overrides[require_salesforce_bearer_token] = lambda: {
        "integration": "salesforce"
    }

    try:
        http_client = TestClient(app)
        response = http_client.post(
            "/api/salesforce/match-company",
            json={
                "query": {"name": "Acme", "country": "de"},
                "options": {"min_score": 0.0, "max_results": 1},
            },
            headers={"Authorization": "Bearer dummy"},
        )

        assert response.status_code == 200
        assert client.calls
        for call in client.calls:
            bool_query = call["body"].get("query", {}).get("bool", {})
            assert bool_query.get("filter") == [{"term": {"country": "DE"}}]
    finally:
        app.dependency_overrides.clear()


def test_match_company_queries_all_name_fields() -> None:
    client = RecordingOSClient()
    app.dependency_overrides[get_os_client] = lambda: client
    app.dependency_overrides[require_salesforce_bearer_token] = lambda: {
        "integration": "salesforce"
    }

    try:
        http_client = TestClient(app)
        response = http_client.post(
            "/api/salesforce/match-company",
            json={"query": {"name": "Gadouche"}},
            headers={"Authorization": "Bearer dummy"},
        )

        assert response.status_code == 200
        assert client.calls
        first_call = client.calls[0]
        bool_query = first_call["body"].get("query", {}).get("bool", {})
        must_clause = bool_query.get("must") or []
        assert any(
            call.get("multi_match", {}).get("fields")
            == ["name_normalized", "name", "name.edge"]
            for call in must_clause
        )
    finally:
        app.dependency_overrides.clear()
