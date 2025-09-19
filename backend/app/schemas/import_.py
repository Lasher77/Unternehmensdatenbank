from datetime import datetime
from pydantic import BaseModel, Field


class ImportResponse(BaseModel):
    import_label: str
    s3_key: str
    task_id: str


class ImportSummaryResponse(BaseModel):
    run_id: int
    summary: dict[str, int] = Field(default_factory=dict)
    finished: bool
    finished_at: datetime | None = None
