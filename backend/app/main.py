from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opensearchpy import OpenSearch
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError
from sqlalchemy import text

from .config import get_settings
from .db import engine
from .opensearch_client import ensure_companies_index, get_opensearch
from .routers import companies, exports, imports, salesforce, search, stats, tasks

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    client = get_opensearch()
    try:
        ensure_companies_index(client)
    except OpenSearchConnectionError as exc:  # pragma: no cover - log-only path
        logger.warning(
            "Skipping OpenSearch index initialization because the cluster is unavailable: %s",
            exc,
        )
    yield


app = FastAPI(title="BVMW Companies API", lifespan=lifespan)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(companies.router)
app.include_router(imports.router)
app.include_router(exports.router)
app.include_router(salesforce.router)
app.include_router(stats.router)
app.include_router(tasks.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        get_opensearch().info()
    except Exception:  # pragma: no cover - simple health check
        return {"status": "unhealthy"}
    return {"status": "ok"}
