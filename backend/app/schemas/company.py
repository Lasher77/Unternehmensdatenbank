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


class CompanyDetailResponse(BaseModel):
    company: Company
    events: List[Event] = []
