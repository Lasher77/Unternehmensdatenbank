import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import db as db_module
from backend.app.main import app


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None


class FakeConnection:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
        sql = getattr(statement, "text", str(statement))
        if "FROM ingestion_run" not in sql:
            raise AssertionError(f"Unexpected SQL: {sql}")
        return FakeResult(self._rows)


class FakeContext:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def __enter__(self) -> FakeConnection:
        return FakeConnection(self._rows)

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
        return False


class FakeEngine:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def begin(self) -> FakeContext:
        return FakeContext(self._rows)


def test_get_import_summary_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    finished_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = [
        {
            "run_id": 7,
            "summary": {"companies": 2, "events": 1},
            "finished_at": finished_at,
        }
    ]

    monkeypatch.setattr(db_module, "engine", FakeEngine(rows))

    client = TestClient(app)
    response = client.get("/api/imports/7")

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "run_id": 7,
        "summary": {"companies": 2, "events": 1},
        "finished": True,
        "finished_at": finished_at.isoformat(),
    }


def test_get_import_summary_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db_module, "engine", FakeEngine([]))

    client = TestClient(app)
    response = client.get("/api/imports/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "Import run not found"
