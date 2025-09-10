from .celery_app import celery_app


@celery_app.task
def run_import(s3_key: str) -> str:
    return s3_key
