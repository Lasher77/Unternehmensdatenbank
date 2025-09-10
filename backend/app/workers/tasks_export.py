from .celery_app import celery_app


@celery_app.task
def run_export(filters: dict[str, str]) -> str:
    return "export-task"
