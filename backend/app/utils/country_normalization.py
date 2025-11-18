"""Utilities for dealing with country codes from various data sources."""

from __future__ import annotations

from typing import Any

_COUNTRY_OVERRIDES: dict[str, str] = {
    # German speaking countries are the most common values in the import.
    "GERMANY": "DE",
    "DEUTSCHLAND": "DE",
    "BUNDESREPUBLIK DEUTSCHLAND": "DE",
    "D": "DE",
    "AUSTRIA": "AT",
    "ÖSTERREICH": "AT",
    "OESTERREICH": "AT",
    "SWITZERLAND": "CH",
    "SCHWEIZ": "CH",
    "SUISSE": "CH",
}


def normalize_country_code(value: Any) -> str | None:
    """Return a sanitized ISO-like country code or ``None``."""

    if value is None:
        return None

    if isinstance(value, str):
        candidate = value.strip()
    else:
        candidate = str(value).strip()

    if not candidate:
        return None

    candidate_upper = candidate.upper()

    override = _COUNTRY_OVERRIDES.get(candidate_upper)
    if override:
        return override

    if len(candidate_upper) in (2, 3):
        return candidate_upper

    return None
