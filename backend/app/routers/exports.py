from fastapi import APIRouter

from ..schemas.export import ExportRequest, ExportResponse

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("", response_model=ExportResponse)
async def create_export(payload: ExportRequest) -> ExportResponse:
    return ExportResponse(task_id="dummy")
