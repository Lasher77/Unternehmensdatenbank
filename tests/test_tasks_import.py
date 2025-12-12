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

    staged_source_ids: list[str] = []

    monkeypatch.setattr(tasks_import, "engine", FakeEngine())
    monkeypatch.setattr(
        tasks_import,
        "map_import_row",
        lambda obj: {"company": {"source_id": obj["id"], "raw_name": obj.get("name", ""), "data": obj}},
    )
    monkeypatch.setattr(
        tasks_import.staging_loader,
        "load_to_staging",
        lambda rows, run_id: staged_source_ids.extend(row["company"]["source_id"] for row in rows),
    )
    monkeypatch.setattr(tasks_import, "get_opensearch", lambda: object())
    monkeypatch.setattr(tasks_import, "ensure_companies_index", lambda client: None)
    monkeypatch.setattr(tasks_import, "index_companies", lambda client, companies: None)
    monkeypatch.setattr(tasks_import.run_import, "update_state", lambda *args, **kwargs: None)

    result = tasks_import.run_import.run(str(data_path), None)

    assert result["successful_records"] == 1
    assert result["error_records"] == 0
    assert result["total_records"] == 2
    assert staged_source_ids == ["dup-1"]
    assert json.loads(tasks_import.engine.update_connection.summary or "{}") == {"companies": 1, "errors": 0}


def test_finalize_import_promotes_and_indexes(monkeypatch: pytest.MonkeyPatch) -> None:
    promoted_runs: list[int] = []
    indexed_companies: list[list[dict[str, Any]]] = []
    finished_calls: list[datetime] = []

    class FakeConnection:
        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
            return False

        def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
            sql = getattr(statement, "text", str(statement))
            params = params or {}

            if "FROM companies" in sql and "seen_in_run" in sql:
                return FakeResult(
                    rows=[
                        {
                            "source_id": "company-1",
                            "name": "Example",
                            "state": None,
                            "city": None,
                            "postal_code": None,
                            "street": None,
                            "country": None,
                            "email": None,
                            "website": None,
                            "phone": None,
                            "register_id": None,
                            "vat_id": None,
                            "status": None,
                            "legal_form": None,
                            "lat": None,
                            "lng": None,
                        }
                    ]
                )

            if "UPDATE ingestion_run" in sql:
                finished_calls.append(params.get("finished_at"))
                return FakeResult()

            raise AssertionError(f"Unexpected SQL: {sql}")

        def begin(self) -> "FakeConnection":
            return self

    class FakeEngine:
        def begin(self) -> FakeConnection:
            return FakeConnection()

    monkeypatch.setattr(tasks_import, "engine", FakeEngine())
    monkeypatch.setattr(tasks_import.staging_loader, "promote_staging", lambda run_id: promoted_runs.append(run_id))
    monkeypatch.setattr(tasks_import, "get_opensearch", lambda: object())
    monkeypatch.setattr(tasks_import, "ensure_companies_index", lambda client: None)
    monkeypatch.setattr(tasks_import, "index_companies", lambda client, companies: indexed_companies.append(companies))

    payload = {"run_id": 99, "file": "example.ndjson"}
    result = tasks_import.finalize_import.run(payload)

    assert result == payload
    assert promoted_runs == [99]
    assert indexed_companies and indexed_companies[0][0]["source_id"] == "company-1"
    assert finished_calls and isinstance(finished_calls[0], datetime)


def test_finalize_import_indexes_raw_name_when_normalized_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    indexed_companies: list[list[dict[str, Any]]] = []

    class FakeConnection:
        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
            return False

        def execute(self, statement: Any, params: dict[str, Any] | None = None) -> FakeResult:
            sql = getattr(statement, "text", str(statement))
            params = params or {}

            if "FROM companies" in sql and "seen_in_run" in sql:
                return FakeResult(
                    rows=[
                        {
                            "source_id": "company-raw",
                            "name": None,
                            "raw_name": "Raw Company GmbH",
                            "state": None,
                            "city": None,
                            "postal_code": None,
                            "street": None,
                            "country": None,
                            "email": None,
                            "website": None,
                            "phone": None,
                            "register_id": None,
                            "vat_id": None,
                            "status": None,
                            "legal_form": None,
                            "lat": None,
                            "lng": None,
                        }
                    ]
                )

            if "UPDATE ingestion_run" in sql:
                return FakeResult()

            raise AssertionError(f"Unexpected SQL: {sql}")

        def begin(self) -> "FakeConnection":
            return self

    class FakeEngine:
        def begin(self) -> FakeConnection:
            return FakeConnection()

    monkeypatch.setattr(tasks_import, "engine", FakeEngine())
    monkeypatch.setattr(tasks_import.staging_loader, "promote_staging", lambda run_id: None)
    monkeypatch.setattr(tasks_import, "get_opensearch", lambda: object())
    monkeypatch.setattr(tasks_import, "ensure_companies_index", lambda client: None)
    monkeypatch.setattr(
        tasks_import,
        "index_companies",
        lambda client, companies: indexed_companies.append(companies),
    )

    payload = {"run_id": 5, "file": "example.ndjson"}
    result = tasks_import.finalize_import.run(payload)

    assert result == payload
    assert indexed_companies
    assert indexed_companies[0][0]["name"] == "Raw Company GmbH"
