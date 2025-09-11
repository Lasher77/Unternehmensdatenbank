from fastapi import APIRouter

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task_status(task_id: str) -> dict[str, int | str]:
    """Return dummy progress for a background task.

    Args:
        task_id: The identifier of the task to check.

    Returns:
        A dictionary containing the task state and progress percentage.
    """
    return {"task_id": task_id, "state": "SUCCESS", "progress": 100}
