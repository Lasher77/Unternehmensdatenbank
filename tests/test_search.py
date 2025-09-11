import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from backend.app.main import app


def test_search_companies() -> None:
    client = TestClient(app)
    response = client.post("/api/search/companies", json={"query": "foo"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["results"] == []
    assert "facets" in data
