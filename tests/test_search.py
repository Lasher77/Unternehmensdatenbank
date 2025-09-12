import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from opensearchpy.exceptions import NotFoundError

from backend.app.deps import get_os_client
from backend.app.main import app


class DummyOSClient:
    def search(self, index: str, body: dict) -> dict:  # pragma: no cover - simple stub
        assert index == "companies"
        return {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {"_source": {"source_id": "1", "name": "Foo"}},
                    {"_source": {"source_id": "2", "name": "Bar"}},
                ],
            },
            "aggregations": {
                "status": {"buckets": [{"key": "active", "doc_count": 2}]}
            },
        }


class DummyMissingIndexClient:
    def search(self, index: str, body: dict) -> dict:  # pragma: no cover - simple stub
        raise NotFoundError(404, {}, "index not found")


def test_search_companies() -> None:
    app.dependency_overrides[get_os_client] = lambda: DummyOSClient()
    client = TestClient(app)
    response = client.post("/api/search/companies", json={"query": "foo"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["results"] == [
        {"source_id": "1", "name": "Foo"},
        {"source_id": "2", "name": "Bar"},
    ]
    assert data["facets"]["status"][0] == {"value": "active", "count": 2}
    app.dependency_overrides.clear()


def test_search_companies_index_missing() -> None:
    app.dependency_overrides[get_os_client] = lambda: DummyMissingIndexClient()
    client = TestClient(app)
    response = client.post("/api/search/companies", json={"query": "foo"})
    assert response.status_code == 404
    assert response.json() == {"detail": "index not found"}
    app.dependency_overrides.clear()


def test_search_companies_no_internal_server_error() -> None:
    """Ensure missing index does not cause a 500 error."""
    app.dependency_overrides[get_os_client] = lambda: DummyMissingIndexClient()
    client = TestClient(app)
    response = client.post("/api/search/companies", json={"query": "foo"})
    assert response.status_code != 500
    app.dependency_overrides.clear()
