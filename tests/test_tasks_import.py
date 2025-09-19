import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.workers import tasks_import


class FakeResult:
    def __init__(self, *, value: Any | None = None, rows: list[dict[str, Any]] | None = None):
        self._value = value
        self._rows = rows or []

    def scalar_one(self) -> Any:
        if self._value is None:
            raise AssertionError("No scalar value available")
        return self._value

    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)


class FakeConnection:
    def __init__(self) -> None:
        self.updated_params: dict[str, Any] | None = None

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
        sql = getattr(statement, "text", str(statement))
        params = params or {}

        if "name_norm AS name" in sql:
            return FakeResult(rows=[{"source_id": "src-1", "name": "Example"}])

        if "COUNT(*) FROM companies" in sql:
            return FakeResult(value=3)
        if "COUNT(*) FROM events" in sql:
            return FakeResult(value=4)
        if "COUNT(*) FROM company_person_roles" in sql:
            return FakeResult(value=5)
        if "COUNT(*) FROM company_industries" in sql:
            return FakeResult(value=6)
        if "COUNT(*) FROM company_relations" in sql:
            return FakeResult(value=7)
        if "COUNT(*) FROM company_history" in sql:
            return FakeResult(value=8)

        if "UPDATE ingestion_run" in sql:
            self.updated_params = dict(params)
            return FakeResult()

        raise AssertionError(f"Unexpected SQL: {sql}")


class FakeConnectionContext:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    def __enter__(self) -> FakeConnection:
        return self._connection

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
        return False


class FakeEngine:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    def begin(self) -> FakeConnectionContext:
        return FakeConnectionContext(self._connection)


def test_finalize_import_collects_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = FakeConnection()
    engine = FakeEngine(connection)

    monkeypatch.setattr(tasks_import, "engine", engine)

    promoted: dict[str, Any] = {}
    monkeypatch.setattr(tasks_import, "promote_staging", lambda run_id: promoted.setdefault("run_id", run_id))

    indexed: dict[str, Any] = {}
    monkeypatch.setattr(tasks_import, "get_opensearch", lambda: object())
    monkeypatch.setattr(tasks_import, "ensure_companies_index", lambda client: indexed.setdefault("ensured", True))
    monkeypatch.setattr(tasks_import, "index_companies", lambda client, rows: indexed.setdefault("rows", list(rows)))

    start = datetime.now(timezone.utc)
    result = tasks_import.finalize_import.run({"s3_key": "file.ndjson", "run_id": 42})

    assert promoted["run_id"] == 42
    assert indexed["ensured"] is True
    assert indexed["rows"] == [{"source_id": "src-1", "name": "Example"}]

    assert result["run_id"] == 42
    assert result["summary"] == {
        "companies": 3,
        "events": 4,
        "company_person_roles": 5,
        "company_industries": 6,
        "company_relations": 7,
        "company_history": 8,
    }

    finished_at = datetime.fromisoformat(result["finished_at"])
    assert finished_at >= start

    assert connection.updated_params is not None
    assert connection.updated_params["run_id"] == 42
    assert json.loads(connection.updated_params["summary"]) == result["summary"]
