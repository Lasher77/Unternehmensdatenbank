from typing import Any, List, Optional

from pydantic import BaseModel, field_validator

_TRUE_VALUES = {"true", "t", "1", "yes", "y"}
_FALSE_VALUES = {"false", "f", "0", "no", "n"}


def _normalize_optional_bool(value: Any) -> bool | None:
    """Return a boolean for known truthy/falsey values, otherwise ``None``."""

    if value is None or isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
        return None

    if isinstance(value, str):
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if cleaned in _TRUE_VALUES:
            return True
        if cleaned in _FALSE_VALUES:
            return False

    return None


class Event(BaseModel):
    event_id: Optional[int] = None
    event_date: Optional[str] = None
    event_type: Optional[str] = None
    description: Optional[str] = None


class Company(BaseModel):
    source_id: str
    raw_name: Optional[str] = None
    legal_form: Optional[str] = None
    name: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    register_id: Optional[str] = None
    register_city: Optional[str] = None
    register_country: Optional[str] = None
    register_unique_key: Optional[str] = None
    status: Optional[str] = None
    terminated: Optional[bool] = None

    @field_validator("terminated", mode="before")
    @classmethod
    def _coerce_terminated(
        cls, value: Any  # noqa: ANN401 - required by pydantic
    ) -> bool | None:
        return _normalize_optional_bool(value)


class CompanyDetailResponse(BaseModel):
    company: Company
    events: List[Event] = []
    persons: List["Person"] = []
    industry_codes: List["IndustryCode"] = []


class PersonRole(BaseModel):
    role_name: Optional[str] = None
    role_type: Optional[str] = None
    role_date: Optional[str] = None


class Person(BaseModel):
    source_person_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    roles: List[PersonRole] = []


class IndustryCode(BaseModel):
    scheme: str
    code: str
