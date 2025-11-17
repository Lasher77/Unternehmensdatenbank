from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.utils import staging_loader
from backend.app.utils.date_normalization import normalize_birth_date


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

        if "INSERT INTO companies" in sql:
            run_id = params["run_id"]
            uses_direct_boolean_cast = "::boolean" in sql

            if uses_direct_boolean_cast:
                for row in self._tables.get("staging_companies", []):
                    if row["run_id"] != run_id:
                        continue

                    company_data = json.loads(row["data"])
                    terminated = company_data.get("terminated")

                    if isinstance(terminated, str) and terminated.lower() not in {
                        "true",
                        "false",
                        "t",
                        "f",
                        "1",
                        "0",
                        "yes",
                        "no",
                        "y",
                        "n",
                    }:
                        raise ValueError(
                            f'invalid input syntax for type boolean: "{terminated}"'
                        )

            self._tables.setdefault("companies", []).append({"sql": sql, "run_id": run_id})
            return

        if "INSERT INTO persons" in sql:
            assert "updated_at" not in sql
            run_id = params["run_id"]
            use_nullif = "NULLIF(btrim(data->>'birthDate'), '')::date" in sql

            self._tables.setdefault("persons_sql", []).append(sql)

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
        "companies": [],
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


def test_load_to_staging_normalizes_terminated(monkeypatch: pytest.MonkeyPatch) -> None:
    tables: dict[str, Any] = {"staging_companies": []}

    fake_engine = FakeEngine(tables)

    from backend.app import db as db_module

    monkeypatch.setattr(db_module, "engine", fake_engine)

    rows = [
        {
            "company": {
                "source_id": "company-1",
                "raw_name": "Example Corp",
                "terminated": "ja",
            }
        }
    ]

    staging_loader.load_to_staging(rows, run_id=1)

    stored = tables["staging_companies"][0]
    company_payload = json.loads(stored["data"])
    assert company_payload["terminated"] is True


def test_promote_staging_normalizes_birthdate(monkeypatch: pytest.MonkeyPatch) -> None:
    tables: dict[str, Any] = {
        "staging_companies": [],
        "staging_persons": [],
        "companies": [],
        "persons": {},
    }

    fake_engine = FakeEngine(tables)

    from backend.app import db as db_module

    monkeypatch.setattr(db_module, "engine", fake_engine)

    raw_birth = "31.05.1978"
    normalized_birth = normalize_birth_date(raw_birth)
    assert normalized_birth == "1978-05-31"

    rows = [
        {
            "company": {"source_id": "company-1", "raw_name": "Example Corp"},
            "persons": [
                {
                    "source_person_id": "person-1",
                    "data": {
                        "name": {"firstName": "Ada", "lastName": "Lovelace"},
                        "birthDate": normalized_birth,
                        "address": {},
                    },
                }
            ],
        }
    ]

    staging_loader.load_to_staging(rows, run_id=1)
    staging_loader.promote_staging(run_id=1)

    promoted = tables["persons"]["person-1"]
    assert promoted["birth_date"] == date(1978, 5, 31)


def test_promote_staging_handles_unparseable_birthdate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tables: dict[str, Any] = {
        "staging_companies": [],
        "staging_persons": [],
        "companies": [],
        "persons": {},
    }

    fake_engine = FakeEngine(tables)

    from backend.app import db as db_module

    monkeypatch.setattr(db_module, "engine", fake_engine)

    assert normalize_birth_date("nicht-datum") is None

    rows = [
        {
            "company": {"source_id": "company-1", "raw_name": "Example Corp"},
            "persons": [
                {
                    "source_person_id": "person-1",
                    "data": {
                        "name": {"firstName": "Ada", "lastName": "Lovelace"},
                        "birthDate": None,
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


def test_promote_staging_deduplicates_persons(monkeypatch: pytest.MonkeyPatch) -> None:
    tables: dict[str, Any] = {
        "staging_companies": [],
        "staging_persons": [],
        "companies": [],
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
                        "birthDate": "1978-05-31",
                        "address": {},
                    },
                },
                {
                    "source_person_id": "person-1",
                    "data": {
                        "name": {"firstName": "A.", "lastName": "Lovelace"},
                        "birthDate": "1978-05-31",
                        "address": {},
                    },
                },
            ],
        }
    ]

    staging_loader.load_to_staging(rows, run_id=1)

    assert len(tables["staging_persons"]) == 2

    staging_loader.promote_staging(run_id=1)

    assert len(tables["persons"]) == 1
    assert "person-1" in tables["persons"]


def test_promote_staging_handles_invalid_terminated_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tables: dict[str, Any] = {
        "staging_companies": [],
        "staging_persons": [],
        "companies": [],
        "persons": {},
    }

    fake_engine = FakeEngine(tables)

    from backend.app import db as db_module

    monkeypatch.setattr(db_module, "engine", fake_engine)

    rows = [
        {
            "company": {
                "source_id": "company-1",
                "raw_name": "Example Corp",
                "terminated": "n/a",
            }
        }
    ]

    staging_loader.load_to_staging(rows, run_id=1)
    staging_loader.promote_staging(run_id=1)

    assert tables["companies"], "expected company insert statement to run"
    for insert in tables["companies"]:
        assert "::boolean" not in insert["sql"]


def test_promote_staging_trims_coordinate_and_country_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tables: dict[str, Any] = {
        "staging_companies": [],
        "staging_persons": [],
        "companies": [],
        "persons": {},
    }

    fake_engine = FakeEngine(tables)

    from backend.app import db as db_module

    monkeypatch.setattr(db_module, "engine", fake_engine)

    rows = [
        {
            "company": {
                "source_id": "company-1",
                "raw_name": "Example Corp",
                "country": "  ",
                "lat": " 52.52 ",
                "lng": "13.40",
            }
        }
    ]

    staging_loader.load_to_staging(rows, run_id=1)
    staging_loader.promote_staging(run_id=1)

    assert tables["companies"], "expected company insert statement to run"
    for insert in tables["companies"]:
        sql = insert["sql"]
        assert (
            "WHEN NULLIF(btrim(data->>'lat'), '') ~ '^[-+]?[0-9]+(\\.[0-9]+)?$'"
            in sql
        )
        assert (
            "WHEN NULLIF(btrim(data->>'lng'), '') ~ '^[-+]?[0-9]+(\\.[0-9]+)?$'"
            in sql
        )
        assert "COALESCE(NULLIF(btrim(data->>'country'), ''), 'DE')" in sql


def test_promote_staging_sanitizes_person_coordinates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tables: dict[str, Any] = {
        "staging_companies": [],
        "staging_persons": [],
        "companies": [],
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
                        "birthDate": "1978-05-31",
                        "address": {"lat": "not-a-number", "lng": "13.4"},
                    },
                }
            ],
        }
    ]

    staging_loader.load_to_staging(rows, run_id=1)
    staging_loader.promote_staging(run_id=1)

    sql_statements = tables.get("persons_sql") or []
    assert sql_statements, "expected person insert statement to run"
    sql = " ".join(sql_statements[-1].split())
    assert (
        "WHEN NULLIF(btrim(data->'address'->>'lat'), '') ~ '^[-+]?[0-9]+(\\.[0-9]+)?$'"
        in sql
    )
    assert (
        "WHEN NULLIF(btrim(data->'address'->>'lng'), '') ~ '^[-+]?[0-9]+(\\.[0-9]+)?$'"
        in sql
    )
