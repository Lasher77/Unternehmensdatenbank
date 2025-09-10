"""Helpers for persisting parsed import data into staging tables."""

from __future__ import annotations

import json
from typing import Dict, List

from sqlalchemy import text


def load_to_staging(rows: List[Dict]) -> None:
    """Insert parsed rows into the ``staging_*`` tables.

    Each row is expected to contain ``company`` and ``events`` keys. The
    function uses a direct SQL approach to avoid ORM overhead.
    """

    if not rows:
        return

    from ..db import engine

    with engine.begin() as conn:
        for row in rows:
            company = row["company"]
            conn.execute(
                text(
                    "INSERT INTO staging_companies (source_id, data, run_id) "
                    "VALUES (:source_id, :data, :run_id)"
                ),
                {
                    "source_id": company["source_id"],
                    "data": json.dumps(company),
                    "run_id": 0,
                },
            )

            for event in row["events"]:
                conn.execute(
                    text(
                        "INSERT INTO staging_events "
                        "(source_id, event_date, event_type, description, run_id) "
                        "VALUES (:source_id, :event_date, :event_type, "
                        ":description, :run_id)"
                    ),
                    {
                        "source_id": company["source_id"],
                        "event_date": event.get("event_date"),
                        "event_type": event.get("event_type"),
                        "description": event.get("description"),
                        "run_id": 0,
                    },
                )
