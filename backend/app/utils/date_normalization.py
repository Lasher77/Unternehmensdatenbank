"""Utilities for normalizing date values from external sources."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

_ALLOWED_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
)


def _iter_parse_formats(value: str, formats: Iterable[str]) -> str | None:
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt).date()
        except ValueError:
            continue
        else:
            return parsed.isoformat()
    return None


def normalize_birth_date(raw: str | None) -> str | None:
    """Normalize a raw birth date value into an ISO formatted string."""

    if raw is None:
        return None

    cleaned = raw.strip()
    if not cleaned:
        return None

    return _iter_parse_formats(cleaned, _ALLOWED_FORMATS)
