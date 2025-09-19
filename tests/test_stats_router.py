import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.deps import get_db_conn
from backend.app.main import app


def test_table_counts_endpoint_returns_counts() -> None:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE companies (id INTEGER, name TEXT)"))
        conn.execute(text("CREATE TABLE events (id INTEGER, description TEXT)"))
        conn.execute(text("INSERT INTO companies (id, name) VALUES (1, 'Acme'), (2, 'Globex')"))
        conn.execute(text("INSERT INTO events (id, description) VALUES (1, 'Launch')"))

    def override_get_db_conn():
        with engine.begin() as conn:
            yield conn

    app.dependency_overrides[get_db_conn] = override_get_db_conn

    client = TestClient(app)
    response = client.get("/api/stats/table-counts")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "counts": [
            {"table": "companies", "rows": 2},
            {"table": "events", "rows": 1},
        ]
    }

    app.dependency_overrides.clear()
