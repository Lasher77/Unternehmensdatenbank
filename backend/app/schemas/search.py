from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CompanySearchRequest(BaseModel):
    query: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    wz: Optional[str] = None
    status: Optional[str] = None
    legal_form: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_km: Optional[float] = None
    sort: Optional[str] = None
    page: int = 1
    per_page: int = 20


class CompanyItem(BaseModel):
    source_id: str
    name: Optional[str] = None


class CompanySearchResponse(BaseModel):
    total: int
    results: List[CompanyItem]
    facets: Dict[str, Dict[str, int]] = Field(default_factory=dict)
