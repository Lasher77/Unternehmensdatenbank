from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opensearchpy import OpenSearch
from sqlalchemy import text
from sqlalchemy.engine import Connection

from .config import get_settings
from .deps import get_db_conn, get_os_client
from .routers import companies, exports, imports, salesforce, search

app = FastAPI(title="BVMW Companies API")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(companies.router)
app.include_router(imports.router)
app.include_router(exports.router)
app.include_router(salesforce.router)


@app.get("/healthz")
def healthz(
    db: Connection = Depends(get_db_conn),
    os_client: OpenSearch = Depends(get_os_client),
) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        os_client.info()
    except Exception:  # pragma: no cover - simple health check
        return {"status": "unhealthy"}
    return {"status": "ok"}
