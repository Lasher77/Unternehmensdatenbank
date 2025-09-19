from fastapi import APIRouter, Depends
from sqlalchemy import MetaData, func, select
from sqlalchemy.engine import Connection

from ..deps import get_db_conn
from ..schemas.stats import TableCount, TableCountsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/table-counts", response_model=TableCountsResponse)
def get_table_counts(db: Connection = Depends(get_db_conn)) -> TableCountsResponse:
    metadata = MetaData()
    reflect_kwargs: dict[str, object] = {}
    if db.dialect.name == "postgresql":
        reflect_kwargs["schema"] = "public"
    metadata.reflect(bind=db, **reflect_kwargs)

    counts = []
    for table in metadata.sorted_tables:
        count_stmt = select(func.count()).select_from(table)
        count = db.execute(count_stmt).scalar_one()
        counts.append(TableCount(table=table.name, rows=count))

    return TableCountsResponse(counts=counts)
