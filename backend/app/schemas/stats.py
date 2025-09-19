from pydantic import BaseModel


class TableCount(BaseModel):
    table: str
    rows: int


class TableCountsResponse(BaseModel):
    counts: list[TableCount]
