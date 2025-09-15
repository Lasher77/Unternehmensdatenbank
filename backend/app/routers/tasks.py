from __future__ import annotations

from typing import Any

from celery import states
from fastapi import APIRouter, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..workers.celery_app import celery_app

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseException):
        return str(value)
    return value


@router.get("/{task_id}")
async def get_task_status(task_id: str) -> JSONResponse:
    """Return the status information for a Celery background task."""

    task_result = celery_app.AsyncResult(task_id)

    response_payload: dict[str, Any] = {
        "task_id": task_id,
        "state": task_result.state,
    }

    info = task_result.info
    if info is not None:
        serialized_info = _serialize(info)
        if serialized_info is not None:
            response_payload["info"] = serialized_info

    task_meta = task_result.backend.get_task_meta(task_id)
    meta = task_meta.get("meta") if isinstance(task_meta, dict) else None
    if meta is not None:
        serialized_meta = _serialize(meta)
        if serialized_meta is not None:
            response_payload["meta"] = serialized_meta

    if task_result.state == states.FAILURE:
        error_detail = response_payload.get("info") or str(task_result.info)
        if error_detail:
            response_payload["error"] = error_detail
        traceback = task_result.traceback
        if traceback:
            response_payload["traceback"] = traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(response_payload),
        )

    return JSONResponse(content=jsonable_encoder(response_payload))
