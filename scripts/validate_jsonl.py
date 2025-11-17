"""Validate a JSONL export before triggering the import task."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


if sys.version_info >= (3, 10):
    dataclass_decorator = dataclass(slots=True)
else:  # pragma: no cover - older Python support
    dataclass_decorator = dataclass


if __package__ is None or __package__ == "":  # pragma: no cover - runtime safety
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.utils.date_normalization import normalize_birth_date

try:
    from backend.app.workers.tasks_import import finalize_import, run_import
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard for tests
    class _DeferredTask:
        """Placeholder to allow tests to patch Celery tasks when dependencies are missing."""

        def __init__(self, name: str) -> None:
            self._name = name

        def apply(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError(
                f"{self._name} ist nicht verfügbar. Fehlt eine optionale Abhängigkeit?",
            )

    run_import = _DeferredTask("run_import")
    finalize_import = _DeferredTask("finalize_import")


@dataclass_decorator
class ValidationReport:
    """Result of validating a JSONL file."""

    errors: list[str]
    duplicate_ids: dict[str, int]

    @property
    def is_valid(self) -> bool:
        """Return ``True`` when the JSONL file passed validation."""

        return not self.errors


def _is_value_set(value: object) -> bool:
    """Return ``True`` when ``value`` contains meaningful data."""

    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _validate_coordinate_value(
    *,
    value: object,
    line_number: int,
    context: str,
    errors: list[str],
) -> None:
    """Append an error when ``value`` cannot be interpreted as float."""

    if not _is_value_set(value):
        return

    if isinstance(value, (int, float)):
        return

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return
        candidate = candidate.replace(",", ".")
    else:
        candidate = str(value)

    try:
        float(candidate)
    except (TypeError, ValueError):
        errors.append(
            f"Zeile {line_number}: {context} enthält keinen numerischen Wert ({value!r})",
        )


def _validate_coordinate_fields(
    address: object,
    *,
    prefix: str,
    line_number: int,
    errors: list[str],
) -> None:
    """Validate ``lat``/``lng`` inside ``address`` when it is a mapping."""

    if not isinstance(address, dict):
        return

    for axis in ("lat", "lng"):
        _validate_coordinate_value(
            value=address.get(axis),
            line_number=line_number,
            context=f"{prefix}.{axis}",
            errors=errors,
        )


def validate_jsonl(jsonl_path: Path) -> ValidationReport:
    """Validate ``jsonl_path`` and return a :class:`ValidationReport`."""

    errors: list[str] = []
    person_counter: Counter[str] = Counter()

    with jsonl_path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"Zeile {line_number}: Ungültiges JSON ({exc.msg})",
                )
                continue

            _validate_coordinate_fields(
                data.get("address"),
                prefix="address",
                line_number=line_number,
                errors=errors,
            )

            related_persons = data.get("relatedPersons")
            if related_persons is None:
                continue

            if not isinstance(related_persons, dict):
                errors.append(
                    f"Zeile {line_number}: relatedPersons muss ein Objekt sein",
                )
                continue

            items = related_persons.get("items", [])
            if not isinstance(items, list):
                errors.append(
                    f"Zeile {line_number}: relatedPersons.items muss eine Liste sein",
                )
                continue

            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(
                        f"Zeile {line_number}: relatedPersons.items[{idx}] muss ein Objekt sein",
                    )
                    continue

                person = item.get("person")
                if not isinstance(person, dict):
                    errors.append(
                        f"Zeile {line_number}: relatedPersons.items[{idx}].person muss ein Objekt sein",
                    )
                    continue

                source_person_id = person.get("id")
                if not _is_value_set(source_person_id):
                    errors.append(
                        f"Zeile {line_number}: relatedPersons.items[{idx}].person.id fehlt",
                    )
                else:
                    person_counter[str(source_person_id)] += 1

                for field in ("name", "address"):
                    if not _is_value_set(person.get(field)):
                        errors.append(
                            "Zeile "
                            f"{line_number}: relatedPersons.items[{idx}].person.{field} fehlt oder ist leer",
                        )

                _validate_coordinate_fields(
                    person.get("address"),
                    prefix=f"relatedPersons.items[{idx}].person.address",
                    line_number=line_number,
                    errors=errors,
                )

                birth_date_raw = person.get("birthDate")
                if _is_value_set(birth_date_raw):
                    normalized_birth_date = normalize_birth_date(str(birth_date_raw))
                    if normalized_birth_date is None:
                        errors.append(
                            "Zeile "
                            f"{line_number}: relatedPersons.items[{idx}].person.birthDate kann nicht interpretiert werden ("
                            f"{birth_date_raw!r})",
                        )

    duplicates = {
        person_id: count for person_id, count in person_counter.items() if count > 1
    }
    sorted_duplicates = dict(sorted(duplicates.items()))
    return ValidationReport(errors=errors, duplicate_ids=sorted_duplicates)


def start_import(jsonl_path: Path) -> dict[str, int | str]:
    """Run the import and finalization tasks for ``jsonl_path`` synchronously."""

    result = run_import.apply(args=[str(jsonl_path)])
    payload = result.get()

    if not isinstance(payload, dict) or "run_id" not in payload:
        raise RuntimeError("Importlauf lieferte kein gültiges Ergebnis zurück")

    run_id = payload["run_id"]
    finalize_result = finalize_import.apply(args=[run_id])
    finalize_result.get()

    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the validation script."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "jsonl_path",
        type=Path,
        help="Pfad zur zu importierenden JSONL-Datei",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate input and, if successful, trigger the import."""

    args = parse_args(argv)
    jsonl_path = args.jsonl_path.expanduser().resolve()

    if not jsonl_path.is_file():
        print(f"Datei nicht gefunden: {jsonl_path}", file=sys.stderr)
        return 2

    report = validate_jsonl(jsonl_path)

    if report.duplicate_ids:
        print("Warnung: Doppelte source_person_id gefunden:", file=sys.stderr)
        for person_id, count in report.duplicate_ids.items():
            print(
                f"  - {person_id} (Vorkommen: {count})",
                file=sys.stderr,
            )

    if not report.is_valid:
        print("Validierung fehlgeschlagen:", file=sys.stderr)
        for message in report.errors:
            print(f"  - {message}", file=sys.stderr)
        return 1

    print("Validierung erfolgreich. Import wird gestartet...")
    start_import(jsonl_path)
    print("Import abgeschlossen.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

