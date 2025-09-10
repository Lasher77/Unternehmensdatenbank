from fastapi import APIRouter

from ..schemas.company import Company, CompanyDetailResponse

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/{source_id}", response_model=CompanyDetailResponse)
def get_company(source_id: str) -> CompanyDetailResponse:
    company = Company(source_id=source_id, raw_name="Dummy")
    return CompanyDetailResponse(company=company, events=[])
