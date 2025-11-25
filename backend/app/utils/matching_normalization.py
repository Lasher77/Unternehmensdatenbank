"""Normalization helpers for Salesforce matching logic."""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_company_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.lower()
    text = text.replace("&", " und ")
    text = re.sub(r"[.,]", " ", text)
    text = re.sub(r"\bco\.?\s*kg\b", "co kg", text)
    text = re.sub(r"\bco\.?\b", "co", text)
    text = re.sub(r"[^a-z0-9äöüß\- ]", " ", text)
    text = _collapse_spaces(text)
    return text or None


def normalize_street(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.lower()
    text = text.replace("ß", "ss")
    text = re.sub(r"straße", "strasse", text)
    text = re.sub(r"\bstr\.\b", "strasse", text)
    text = re.sub(r"\bstr\b", "strasse", text)
    text = re.sub(r"[.,]", " ", text)
    text = re.sub(r"[^a-z0-9äöüß\- ]", " ", text)
    text = _collapse_spaces(text)
    return text or None


def normalize_city(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.lower()
    text = re.sub(r"[^a-z0-9äöüß\- ]", " ", text)
    return _collapse_spaces(text) or None


def normalize_postal_code(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = re.sub(r"\s+", "", value)
    return text or None


def normalize_domain(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip().lower()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"http://{candidate}"
    parsed = urlparse(candidate)
    domain = parsed.netloc or parsed.path
    domain = domain.lstrip("www.")
    domain = domain.rstrip("/")
    return domain or None
