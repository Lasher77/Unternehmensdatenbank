from pydantic import BaseModel


class ImportResponse(BaseModel):
    import_label: str
    s3_key: str
    task_id: str
