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


class ImportErrorEntry(BaseModel):
    run_id: int
    source_id: str | None = None
    line_number: int | None = None
    file_name: str
    error_code: str
    error_message: str
    raw_excerpt: str | None = None


class ImportErrorListResponse(BaseModel):
    run_id: int
    total: int
    offset: int
    limit: int
    errors: list[ImportErrorEntry]
