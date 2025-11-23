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
    def __init__(self, *, rows: list[dict[str, Any]] | None = None, scalar: int | None = None):
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> "FakeResult":
        return self

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def scalar_one(self) -> int:
        if self._scalar is None:
            raise AssertionError("No scalar value available")
        return self._scalar


class FakeConnection:
    def __init__(self, *, runs: list[dict[str, Any]], errors: list[dict[str, Any]]):
        self._runs = runs
        self._errors = errors

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
        sql = getattr(statement, "text", str(statement))
        params = params or {}

        if "FROM ingestion_run" in sql:
            return FakeResult(rows=self._runs)

        if "FROM ingestion_errors" in sql:
            filtered = [row for row in self._errors if row["run_id"] == params.get("run_id")]
            if "COUNT(*)" in sql:
                return FakeResult(scalar=len(filtered))

            offset = params.get("offset", 0)
            limit = params.get("limit", len(filtered))
            return FakeResult(rows=filtered[offset : offset + limit])

        raise AssertionError(f"Unexpected SQL: {sql}")


class FakeContext:
    def __init__(self, *, runs: list[dict[str, Any]], errors: list[dict[str, Any]]):
        self._runs = runs
        self._errors = errors

    def __enter__(self) -> FakeConnection:
        return FakeConnection(runs=self._runs, errors=self._errors)

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
        return False


class FakeEngine:
    def __init__(self, *, runs: list[dict[str, Any]], errors: list[dict[str, Any]]):
        self._runs = runs
        self._errors = errors

    def begin(self) -> FakeContext:
        return FakeContext(runs=self._runs, errors=self._errors)


def test_get_import_summary_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    finished_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = [
        {
            "run_id": 7,
            "summary": {"companies": 2, "events": 1},
            "finished_at": finished_at,
        }
    ]

    monkeypatch.setattr(db_module, "engine", FakeEngine(runs=rows, errors=[]))

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
    monkeypatch.setattr(db_module, "engine", FakeEngine(runs=[], errors=[]))

    client = TestClient(app)
    response = client.get("/api/imports/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "Import run not found"


def test_list_import_errors_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    finished_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    runs = [
        {
            "run_id": 7,
            "summary": {"companies": 0, "errors": 2},
            "finished_at": finished_at,
        }
    ]
    errors = [
        {
            "run_id": 7,
            "source_id": "src-1",
            "line_number": 5,
            "file_name": "file.jsonl",
            "error_code": "JSON_PARSE_ERROR",
            "error_message": "unexpected character",
            "raw_excerpt": "{...}",
        },
        {
            "run_id": 7,
            "source_id": None,
            "line_number": 8,
            "file_name": "file.jsonl",
            "error_code": "MISSING_SOURCE_ID",
            "error_message": "missing id",
            "raw_excerpt": None,
        },
    ]

    monkeypatch.setattr(db_module, "engine", FakeEngine(runs=runs, errors=errors))

    client = TestClient(app)
    response = client.get("/api/imports/7/errors", params={"offset": 1, "limit": 1})

    assert response.status_code == 200
    data = response.json()

    assert data == {
        "run_id": 7,
        "total": 2,
        "offset": 1,
        "limit": 1,
        "errors": [
            {
                "run_id": 7,
                "source_id": None,
                "line_number": 8,
                "file_name": "file.jsonl",
                "error_code": "MISSING_SOURCE_ID",
                "error_message": "missing id",
                "raw_excerpt": None,
            }
        ],
    }


def test_list_import_errors_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db_module, "engine", FakeEngine(runs=[], errors=[]))

    client = TestClient(app)
    response = client.get("/api/imports/404/errors")

    assert response.status_code == 404
    assert response.json()["detail"] == "Import run not found"
