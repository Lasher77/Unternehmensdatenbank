from fastapi import APIRouter, Form, UploadFile

from ..schemas.import_ import ImportResponse

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("", response_model=ImportResponse)
async def create_import(
    label: str = Form(...), file: UploadFile | None = None
) -> ImportResponse:
    filename = file.filename if file else ""
    return ImportResponse(import_label=label, s3_key=filename, task_id="dummy")
