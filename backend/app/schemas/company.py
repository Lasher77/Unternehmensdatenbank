from typing import List, Optional

from pydantic import BaseModel


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
