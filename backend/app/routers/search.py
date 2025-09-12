from fastapi import APIRouter, Depends, HTTPException
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError

from ..deps import get_os_client
from ..schemas.search import CompanySearchRequest, CompanySearchResponse
from .. import search as search_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("/companies", response_model=CompanySearchResponse)
def search_companies(
    request: CompanySearchRequest,
    client: OpenSearch = Depends(get_os_client),
) -> CompanySearchResponse:
    try:
        result = search_service.search_companies(client, request.model_dump())
    except NotFoundError:
        raise HTTPException(status_code=404, detail="index not found")
    return CompanySearchResponse(**result)
