from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.validate_jsonl as validate_jsonl_module
from scripts.validate_jsonl import ValidationReport, start_import, validate_jsonl


def write_jsonl(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "data.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")
    return path


def valid_person(person_id: str) -> dict:
    return {
        "person": {
            "id": person_id,
            "name": "Max Mustermann",
            "address": {"city": "Berlin"},
            "birthDate": "1990-01-01",
        }
    }


def test_validate_jsonl_success(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "relatedPersons": {"items": [valid_person("person-1")]},
            }
        ],
    )

    report = validate_jsonl(path)

    assert isinstance(report, ValidationReport)
    assert report.is_valid
    assert report.errors == []
    assert report.duplicate_ids == {}


def test_validate_jsonl_reports_missing_fields(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "relatedPersons": {
                    "items": [
                        {
                            "person": {
                                "id": "",
                                "name": "",
                                "address": {},
                                "birthDate": "",
                            }
                        }
                    ]
                },
            }
        ],
    )

    report = validate_jsonl(path)

    assert not report.is_valid
    assert any("person.id" in error for error in report.errors)
    assert any("person.name" in error for error in report.errors)
    assert any("person.address" in error for error in report.errors)
    assert all("person.birthDate fehlt" not in error for error in report.errors)


def test_validate_jsonl_accepts_missing_birthdate(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "relatedPersons": {
                    "items": [
                        {
                            "person": {
                                "id": "person-1",
                                "name": "Max Mustermann",
                                "address": {"city": "Berlin"},
                            }
                        }
                    ]
                },
            }
        ],
    )

    report = validate_jsonl(path)

    assert report.is_valid
    assert report.errors == []


def test_validate_jsonl_finds_duplicate_ids(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "relatedPersons": {"items": [valid_person("person-1")]},
            },
            {
                "id": "company-2",
                "relatedPersons": {"items": [valid_person("person-1")]},
            },
        ],
    )

    report = validate_jsonl(path)

    assert report.is_valid
    assert report.duplicate_ids == {"person-1": 2}


def test_validate_jsonl_accepts_alternative_birthdate_format(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "relatedPersons": {
                    "items": [
                        {
                            "person": {
                                "id": "person-1",
                                "name": "Max Mustermann",
                                "address": {"city": "Berlin"},
                                "birthDate": "31.05.1978",
                            }
                        }
                    ]
                },
            }
        ],
    )

    report = validate_jsonl(path)

    assert report.is_valid
    assert report.errors == []


def test_validate_jsonl_reports_unparseable_birthdate(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "relatedPersons": {
                    "items": [
                        {
                            "person": {
                                "id": "person-1",
                                "name": "Max Mustermann",
                                "address": {"city": "Berlin"},
                                "birthDate": "31.05.78",
                            }
                        }
                    ]
                },
            }
        ],
    )

    report = validate_jsonl(path)

    assert not report.is_valid
    assert any("birthDate kann nicht interpretiert" in error for error in report.errors)


def test_validate_jsonl_reports_invalid_company_coordinates(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "address": {"lat": "foo", "lng": "13.37"},
            }
        ],
    )

    report = validate_jsonl(path)

    assert not report.is_valid
    assert any("address.lat" in error for error in report.errors)


def test_validate_jsonl_reports_invalid_person_coordinates(tmp_path: Path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "relatedPersons": {
                    "items": [
                        {
                            "person": {
                                "id": "person-1",
                                "name": "Max Mustermann",
                                "address": {"city": "Berlin", "lat": "foo"},
                                "birthDate": "1990-01-01",
                            }
                        }
                    ]
                },
            }
        ],
    )

    report = validate_jsonl(path)

    assert not report.is_valid
    assert any(
        "relatedPersons.items[0].person.address.lat" in error for error in report.errors
    )


class DummyResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def get(self, timeout: float | None = None) -> Any:  # pragma: no cover - signature parity
        return self._value


def test_start_import_promotes_without_worker(monkeypatch, tmp_path: Path) -> None:
    tables: dict[str, list[dict[str, Any]]] = {"staging": [], "companies": []}
    promoted_run_ids: list[int] = []

    def fake_run_import_apply(*, args=None, kwargs=None, **_: Any) -> DummyResult:
        args = args or ()
        jsonl_arg = args[0] if args else kwargs["jsonl_path"]
        jsonl_path = Path(jsonl_arg)
        run_id = 42

        with jsonl_path.open(encoding="utf-8") as handle:
            for line in handle:
                data = line.strip()
                if not data:
                    continue
                tables["staging"].append({"run_id": run_id, "company": json.loads(data)})

        return DummyResult({"s3_key": str(jsonl_path), "run_id": run_id})

    def fake_finalize_import_apply(*, args=None, kwargs=None, **_: Any) -> DummyResult:
        args = args or ()
        run_id = args[0] if args else kwargs["run_id"]
        promoted_run_ids.append(run_id)

        for row in list(tables["staging"]):
            if row["run_id"] == run_id:
                tables["companies"].append(row["company"])
                tables["staging"].remove(row)

        return DummyResult(run_id)

    monkeypatch.setattr(validate_jsonl_module.run_import, "apply", fake_run_import_apply)
    monkeypatch.setattr(validate_jsonl_module.finalize_import, "apply", fake_finalize_import_apply)

    jsonl_path = write_jsonl(
        tmp_path,
        [
            {
                "id": "company-1",
                "relatedPersons": {"items": []},
            }
        ],
    )

    result = start_import(jsonl_path)

    assert result == {"s3_key": str(jsonl_path), "run_id": 42}
    assert promoted_run_ids == [42]
    assert tables["staging"] == []
    assert [company["id"] for company in tables["companies"]] == ["company-1"]
