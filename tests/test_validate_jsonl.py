from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_jsonl import ValidationReport, validate_jsonl


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
    assert any("person.birthDate" in error for error in report.errors)


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
