from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.utils import staging_loader


class FakeConnection:
    def __init__(self, tables: dict[str, Any]) -> None:
        self._tables = tables

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> None:
        sql = getattr(statement, "text", str(statement))
        params = params or {}

        if "INSERT INTO staging_companies" in sql:
            self._tables.setdefault("staging_companies", []).append(dict(params))
            return

        if "INSERT INTO staging_persons" in sql:
            self._tables.setdefault("staging_persons", []).append(dict(params))
            return

        if "INSERT INTO persons" in sql:
            run_id = params["run_id"]
            use_nullif = "NULLIF(data->>'birthDate', '')::date" in sql

            for row in list(self._tables.get("staging_persons", [])):
                if row["run_id"] != run_id:
                    continue

                person_data = json.loads(row["data"])
                raw_birth = person_data.get("birthDate")

                if use_nullif and raw_birth == "":
                    cast_input: str | None = None
                else:
                    cast_input = raw_birth

                if cast_input == "":
                    raise ValueError('invalid input syntax for type date: ""')

                birth_date = date.fromisoformat(cast_input) if cast_input else None

                self._tables.setdefault("persons", {})[
                    row["source_person_id"]
                ] = {"birth_date": birth_date}

            return

        # Ignore other SQL statements used by staging promotion.
        return


class FakeConnectionContext:
    def __init__(self, tables: dict[str, Any]) -> None:
        self._tables = tables
        self._connection = FakeConnection(tables)

    def __enter__(self) -> FakeConnection:
        return self._connection

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
        return False


class FakeEngine:
    def __init__(self, tables: dict[str, Any]) -> None:
        self._tables = tables

    def begin(self) -> FakeConnectionContext:
        return FakeConnectionContext(self._tables)


def test_promote_staging_allows_empty_birthdate(monkeypatch: pytest.MonkeyPatch) -> None:
    tables: dict[str, Any] = {
        "staging_companies": [],
        "staging_persons": [],
        "persons": {},
    }

    fake_engine = FakeEngine(tables)

    from backend.app import db as db_module

    monkeypatch.setattr(db_module, "engine", fake_engine)

    rows = [
        {
            "company": {"source_id": "company-1", "raw_name": "Example Corp"},
            "persons": [
                {
                    "source_person_id": "person-1",
                    "data": {
                        "name": {"firstName": "Ada", "lastName": "Lovelace"},
                        "birthDate": "",
                        "address": {},
                    },
                }
            ],
        }
    ]

    staging_loader.load_to_staging(rows, run_id=1)
    staging_loader.promote_staging(run_id=1)

    promoted = tables["persons"]["person-1"]
    assert promoted["birth_date"] is None
