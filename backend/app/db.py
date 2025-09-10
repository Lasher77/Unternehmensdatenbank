from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import get_settings

settings = get_settings()

DATABASE_URL = (
    f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
)

engine: Engine = create_engine(DATABASE_URL, future=True)


def get_db() -> Generator:
    with engine.begin() as conn:
        yield conn
