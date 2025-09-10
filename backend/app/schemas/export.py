from typing import List, Optional

from pydantic import BaseModel


class ExportRequest(BaseModel):
    format: str
    columns: Optional[List[str]] = None
    q: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    wz: Optional[str] = None
    status: Optional[str] = None
    legal_form: Optional[str] = None
    selected_ids: Optional[List[str]] = None


class ExportResponse(BaseModel):
    task_id: str
