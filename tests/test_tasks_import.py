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


def test_run_import_ignores_duplicate_source_ids(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data_path = tmp_path / "duplicates.ndjson"
    data_path.write_text("\n".join(json.dumps({"id": "dup-1", "name": name}) for name in ["A", "B"]))

    class FakeResult:
        def __init__(self, *, value: Any | None = None, rows: list[dict[str, Any]] | None = None):
            self._value = value
            self._rows = rows or []

        def scalar_one(self) -> Any:
            return self._value

        def mappings(self) -> "FakeResult":
            return self

        def all(self) -> list[dict[str, Any]]:
            return list(self._rows)

    class FakeConnection:
        def __init__(self) -> None:
            self.summary: str | None = None

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
            return False

        def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
            sql = getattr(statement, "text", str(statement))
            params = params or {}

            if "INSERT INTO ingestion_run" in sql:
                return FakeResult(value=1)

            if "FROM companies" in sql:
                source_id = params["source_ids"][0]
                return FakeResult(
                    rows=[
                        {
                            "source_id": source_id,
                            "name": "Example",
                            "state": None,
                            "city": None,
                            "postal_code": None,
                            "status": None,
                            "legal_form": None,
                            "lat": None,
                            "lng": None,
                        }
                    ]
                )

            if "UPDATE ingestion_run" in sql:
                self.summary = params.get("summary")
                return FakeResult()

            raise AssertionError(f"Unexpected SQL: {sql}")

        def commit(self) -> None:
            return None

        def begin(self) -> "FakeConnection":
            return self

    class FakeEngine:
        def __init__(self) -> None:
            self.connection = FakeConnection()
            self.update_connection = FakeConnection()

        def connect(self) -> FakeConnection:
            return self.connection

        def begin(self) -> FakeConnection:
            return self.update_connection

    upserts: list[str] = []

    monkeypatch.setattr(tasks_import, "engine", FakeEngine())
    monkeypatch.setattr(
        tasks_import,
        "map_company_payload",
        lambda obj: {"source_id": obj["id"], "raw_name": obj.get("name", ""), "data": obj},
    )
    monkeypatch.setattr(tasks_import, "_upsert_company", lambda conn, company, run_id: upserts.append(company["source_id"]))
    monkeypatch.setattr(tasks_import, "get_opensearch", lambda: object())
    monkeypatch.setattr(tasks_import, "ensure_companies_index", lambda client: None)
    monkeypatch.setattr(tasks_import, "index_companies", lambda client, companies: None)
    monkeypatch.setattr(tasks_import.run_import, "update_state", lambda *args, **kwargs: None)

    result = tasks_import.run_import.run(str(data_path), None)

    assert result["successful_records"] == 1
    assert result["error_records"] == 0
    assert result["total_records"] == 2
    assert upserts == ["dup-1"]
    assert json.loads(tasks_import.engine.update_connection.summary or "{}") == {"companies": 1, "errors": 0}
