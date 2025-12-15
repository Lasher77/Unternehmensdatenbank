"""Utility to apply SQL migrations in order.

This script ensures each migration runs at most once by recording executed
filenames in the ``schema_migrations`` table. It can be used from Docker
containers and local development environments alike.
"""

from __future__ import annotations

import logging
from contextlib import closing
from pathlib import Path

from psycopg2 import Error
from sqlalchemy.engine import Engine

from backend.app.db import engine as default_engine

LOGGER = logging.getLogger(__name__)

# SQLSTATE error codes that indicate an idempotent migration has already been
# applied. These cover duplicate column/constraint/index definitions produced
# when re-running ALTER/CREATE statements.
IGNORED_SQLSTATES: set[str] = {"42701", "42P07", "42710"}


def _get_migration_paths() -> list[Path]:
    root_dir = Path(__file__).resolve().parents[1]
    migrations_dir = root_dir / "migrations"
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")
    return sorted(migrations_dir.glob("*.sql"))


def apply_migrations(db_engine: Engine | None = None) -> None:
    paths = _get_migration_paths()
    if not paths:
        LOGGER.info("No migrations found, skipping.")
        return

    engine_to_use = db_engine or default_engine
    raw_conn_factory = getattr(engine_to_use, "raw_connection", None)
    if raw_conn_factory is None:
        LOGGER.info("Skipping migrations: engine does not provide raw_connection().")
        return

    raw_conn = raw_conn_factory()
    try:
        if hasattr(raw_conn, "autocommit"):
            raw_conn.autocommit = True
        elif hasattr(raw_conn, "isolation_level"):
            raw_conn.isolation_level = None

        with closing(raw_conn.cursor()) as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            for path in paths:
                filename = path.name
                cursor.execute(
                    "SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,)
                )
                if cursor.fetchone():
                    LOGGER.info("Skipping %s (already applied).", filename)
                    continue

                sql = path.read_text(encoding="utf-8").strip()
                if not sql:
                    LOGGER.info("Skipping %s (empty file).", filename)
                    cursor.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (filename,),
                    )
                    continue

                LOGGER.info("Applying migration %s", filename)
                record_as_applied = False
                try:
                    cursor.execute(sql)
                except Error as exc:  # pragma: no cover - defensive
                    raw_conn.rollback()
                    if getattr(exc, "pgcode", None) in IGNORED_SQLSTATES:
                        LOGGER.info(
                            "Migration %s already applied (%s), recording as completed.",
                            filename,
                            exc.pgcode,
                        )
                        record_as_applied = True
                    else:
                        LOGGER.error(
                            "Failed to apply migration %s: %s", filename, exc.pgerror
                        )
                        raise
                else:
                    record_as_applied = True
                    LOGGER.info("Migration %s applied successfully", filename)

                if record_as_applied:
                    cursor.execute(
                        """
                        INSERT INTO schema_migrations (filename)
                        VALUES (%s)
                        ON CONFLICT (filename) DO NOTHING
                        """,
                        (filename,),
                    )
    finally:
        raw_conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    apply_migrations()
