import json
from fastapi import APIRouter, Form, HTTPException, UploadFile
from pathlib import Path
from tempfile import NamedTemporaryFile

from sqlalchemy import text

from ..db import engine
from ..workers.tasks_import import cleanup_import_file, finalize_import, run_import

from ..schemas.import_ import ImportResponse, ImportSummaryResponse

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

        workflow = run_import.s(temp_path) | finalize_import.s() | cleanup_import_file.s()
        task = workflow.apply_async()
        task_id = task.id
    else:
        task_id = ""

    return ImportResponse(
        import_label=label,
        s3_key=filename,
        task_id=task_id,
    )


@router.get("/{run_id}", response_model=ImportSummaryResponse)
def get_import_summary(run_id: int) -> ImportSummaryResponse:
    with engine.begin() as conn:
        row = (
            conn.execute(
                text(
                    """
                    SELECT run_id, finished_at, summary
                    FROM ingestion_run
                    WHERE run_id = :run_id
                    """
                ),
                {"run_id": run_id},
            )
            .mappings()
            .first()
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Import run not found")

    summary_value = row.get("summary")
    if isinstance(summary_value, str):
        summary = json.loads(summary_value)
    elif summary_value is None:
        summary = {}
    else:
        summary = dict(summary_value)

    finished_at = row.get("finished_at")

    return ImportSummaryResponse(
        run_id=row["run_id"],
        summary=summary,
        finished=finished_at is not None,
        finished_at=finished_at,
    )
