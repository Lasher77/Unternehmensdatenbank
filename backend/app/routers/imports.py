from fastapi import APIRouter, Form, UploadFile
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..workers.tasks_import import cleanup_import_file, run_import

from ..schemas.import_ import ImportResponse

router = APIRouter(prefix="/api/imports", tags=["imports"])


IMPORTS_DIR = Path("/data/imports")


@router.post("", response_model=ImportResponse)
async def create_import(
    label: str = Form(...), file: UploadFile | None = None
) -> ImportResponse:
    filename = file.filename if file else ""
    if file:
        suffix = Path(filename).suffix if filename else ""

        await file.seek(0)
        IMPORTS_DIR.mkdir(parents=True, exist_ok=True)

        with NamedTemporaryFile(delete=False, dir=IMPORTS_DIR, suffix=suffix) as tmp:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
            temp_path = tmp.name

        await file.close()

        task = run_import.apply_async(
            args=[temp_path],
            link=cleanup_import_file.s(),
        )
        task_id = task.id
    else:
        task_id = ""

    return ImportResponse(
        import_label=label,
        s3_key=filename,
        task_id=task_id,
    )
