from fastapi import APIRouter, Depends
from opensearchpy import OpenSearch

from ..deps import get_os_client
from ..schemas.search import CompanySearchRequest, CompanySearchResponse
from .. import search as search_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/companies", response_model=CompanySearchResponse)
def search_companies(
    request: CompanySearchRequest,
    client: OpenSearch = Depends(get_os_client),
) -> CompanySearchResponse:
    result = search_service.search_companies(client, request.model_dump())
    return CompanySearchResponse(**result)
