"""Schemas for the Salesforce matching endpoint."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SalesforceMatchContext(BaseModel):
    source: Optional[str] = None
    object_type: Optional[str] = None
    external_id: Optional[str] = None


class SalesforceMatchQuery(BaseModel):
    name: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    register_id: Optional[str] = None
    vat_id: Optional[str] = None


class SalesforceMatchOptions(BaseModel):
    max_results: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=0, le=1)


class SalesforceMatchRequest(BaseModel):
    context: Optional[SalesforceMatchContext] = None
    query: SalesforceMatchQuery
    options: Optional[SalesforceMatchOptions] = None


class SalesforceMatchedCompany(BaseModel):
    source_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    revenue: Optional[float] = None
    register_id: Optional[str] = None
    vat_id: Optional[str] = None
    status: Optional[str] = None


class SalesforceMatchItem(BaseModel):
    source_id: str
    score: float
    match_type: str
    company: SalesforceMatchedCompany
    reasons: List[str] = Field(default_factory=list)


class SalesforceMatchResult(BaseModel):
    company: Optional[SalesforceMatchedCompany] = None
    match_level: str
    confidence: float


class SalesforceMatchThresholds(BaseModel):
    auto_link: float = 0.9
    review: float = 0.7


class SalesforceMatchResponse(BaseModel):
    matches: List[SalesforceMatchItem]
    best_match: Optional[SalesforceMatchItem] = None
    result: SalesforceMatchResult
    thresholds: SalesforceMatchThresholds = Field(
        default_factory=SalesforceMatchThresholds
    )
