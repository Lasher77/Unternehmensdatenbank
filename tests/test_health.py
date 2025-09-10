from fastapi.testclient import TestClient

from backend.app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert "status" in response.json()
