"""Helpers for persisting parsed import data into staging tables."""

from __future__ import annotations

import json
from typing import Dict, List

from sqlalchemy import text


def load_to_staging(rows: List[Dict], run_id: int) -> None:
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
                    "run_id": run_id,
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
                        "run_id": run_id,
                    },
                )


def promote_staging(run_id: int) -> None:
    """Move data from staging tables into the main ``companies`` and ``events`` tables.

    The function performs an ``UPSERT`` into ``companies`` using ``source_id`` as
    unique identifier and replaces existing events for the affected companies.
    ``ingestion_run`` references are preserved via the ``run_id`` column.
    """

    from ..db import engine

    with engine.begin() as conn:
        # Upsert companies
        conn.execute(
            text(
                """
                INSERT INTO companies (
                    source_id, raw_name, legal_form, name_norm, street,
                    postal_code, city, state, country, lat, lng,
                    register_id, register_city, register_country,
                    register_unique_key, status, terminated, data, seen_in_run
                )
                SELECT
                    source_id,
                    data->>'raw_name',
                    data->>'legal_form',
                    data->>'name',
                    data->>'street',
                    data->>'postal_code',
                    data->>'city',
                    data->>'state',
                    COALESCE(data->>'country', 'DE'),
                    (data->>'lat')::double precision,
                    (data->>'lng')::double precision,
                    data->>'register_id',
                    data->>'register_city',
                    data->>'register_country',
                    data->>'register_unique_key',
                    data->>'status',
                    (data->>'terminated')::boolean,
                    data,
                    run_id
                FROM staging_companies
                WHERE run_id = :run_id
                ON CONFLICT (source_id) DO UPDATE SET
                    raw_name = EXCLUDED.raw_name,
                    legal_form = EXCLUDED.legal_form,
                    name_norm = EXCLUDED.name_norm,
                    street = EXCLUDED.street,
                    postal_code = EXCLUDED.postal_code,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    country = EXCLUDED.country,
                    lat = EXCLUDED.lat,
                    lng = EXCLUDED.lng,
                    register_id = EXCLUDED.register_id,
                    register_city = EXCLUDED.register_city,
                    register_country = EXCLUDED.register_country,
                    register_unique_key = EXCLUDED.register_unique_key,
                    status = EXCLUDED.status,
                    terminated = EXCLUDED.terminated,
                    data = EXCLUDED.data,
                    seen_in_run = EXCLUDED.seen_in_run,
                    updated_at = now()
                """
            ),
            {"run_id": run_id},
        )

        # Replace events for affected companies
        conn.execute(
            text(
                """
                DELETE FROM events WHERE source_id IN (
                    SELECT source_id FROM staging_events WHERE run_id = :run_id
                )
                """
            ),
            {"run_id": run_id},
        )

        conn.execute(
            text(
                """
                INSERT INTO events (
                    source_id, event_date, event_type, description, run_id
                )
                SELECT source_id, event_date, event_type, description, run_id
                FROM staging_events
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        )
