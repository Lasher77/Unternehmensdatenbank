"""Helpers for persisting parsed import data into staging tables."""

from __future__ import annotations

import json
from typing import Dict, List

from sqlalchemy import text


def load_to_staging(rows: List[Dict], run_id: int) -> None:
    """Insert parsed rows into the ``staging_*`` tables.

    Each row may contain ``company`` data along with related ``events``,
    ``persons`` with their roles, and ``industries``. The function uses a
    direct SQL approach to avoid ORM overhead.
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

            for event in row.get("events", []):
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

            for person in row.get("persons", []):
                conn.execute(
                    text(
                        "INSERT INTO staging_persons "
                        "(source_person_id, data, run_id) "
                        "VALUES (:source_person_id, :data, :run_id)"
                    ),
                    {
                        "source_person_id": person["source_person_id"],
                        "data": json.dumps(person["data"]),
                        "run_id": run_id,
                    },
                )

            for role in row.get("roles", []):
                if role is None:
                    continue
                conn.execute(
                    text(
                        "INSERT INTO staging_company_person_roles "
                        "("
                        "source_id, source_person_id, role_name, "
                        "role_type, role_date, description, demotion, run_id"
                        ") "
                        "VALUES (:source_id, :source_person_id, :role_name, "
                        ":role_type, :role_date, :description, :demotion, :run_id)"
                    ),
                    {
                        "source_id": role.get("source_id"),
                        "source_person_id": role.get("source_person_id"),
                        "role_name": role.get("role_name"),
                        "role_type": role.get("role_type"),
                        "role_date": role.get("role_date"),
                        "description": role.get("description"),
                        "demotion": role.get("demotion"),
                        "run_id": run_id,
                    },
                )

            for industry in row.get("industries", []):
                conn.execute(
                    text(
                        "INSERT INTO staging_company_industries "
                        "(source_id, scheme, code, run_id) "
                        "VALUES (:source_id, :scheme, :code, :run_id)"
                    ),
                    {
                        "source_id": industry.get("source_id"),
                        "scheme": industry.get("scheme"),
                        "code": industry.get("code"),
                        "run_id": run_id,
                    },
                )

            for relation in row.get("relations", []):
                conn.execute(
                    text(
                        """
                        INSERT INTO staging_company_relations (
                            source_id,
                            related_source_id,
                            relation_type,
                            description,
                            run_id
                        )
                        VALUES (
                            :source_id,
                            :related_source_id,
                            :relation_type,
                            :description,
                            :run_id
                        )
                        """
                    ),
                    {
                        "source_id": relation.get("source_id"),
                        "related_source_id": relation.get("related_source_id"),
                        "relation_type": relation.get("relation_type"),
                        "description": relation.get("description"),
                        "run_id": run_id,
                    },
                )


def promote_staging(run_id: int) -> None:
    """Move data from staging tables into the main tables.

    The function performs ``UPSERT`` operations for companies and persons and
    replaces existing events, roles and industries for the affected companies.
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

        # Upsert persons
        conn.execute(
            text(
                """
                INSERT INTO persons (
                    source_person_id, first_name, last_name, birth_date,
                    street, postal_code, city, state, country, lat, lng, data
                )
                SELECT
                    source_person_id,
                    data->'name'->>'firstName',
                    data->'name'->>'lastName',
                    (data->>'birthDate')::date,
                    data->'address'->>'street',
                    data->'address'->>'postalCode',
                    data->'address'->>'city',
                    data->'address'->>'state',
                    COALESCE(data->'address'->>'country', 'DE'),
                    (data->'address'->>'lat')::double precision,
                    (data->'address'->>'lng')::double precision,
                    data
                FROM staging_persons
                WHERE run_id = :run_id
                ON CONFLICT (source_person_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    birth_date = EXCLUDED.birth_date,
                    street = EXCLUDED.street,
                    postal_code = EXCLUDED.postal_code,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    country = EXCLUDED.country,
                    lat = EXCLUDED.lat,
                    lng = EXCLUDED.lng,
                    data = EXCLUDED.data
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

        # Replace roles for affected companies
        conn.execute(
            text(
                """
                DELETE FROM company_person_roles WHERE source_id IN (
                    SELECT source_id
                    FROM staging_company_person_roles
                    WHERE run_id = :run_id
                )
                """
            ),
            {"run_id": run_id},
        )

        conn.execute(
            text(
                """
                INSERT INTO company_person_roles (
                    source_id,
                    person_id,
                    role_name,
                    role_type,
                    role_date,
                    description,
                    demotion,
                    run_id
                )
                SELECT
                    scpr.source_id,
                    p.person_id,
                    scpr.role_name,
                    scpr.role_type,
                    scpr.role_date,
                    scpr.description,
                    scpr.demotion,
                    scpr.run_id
                FROM staging_company_person_roles scpr
                JOIN persons p ON p.source_person_id = scpr.source_person_id
                WHERE scpr.run_id = :run_id
                """
            ),
            {"run_id": run_id},
        )

        # Replace industries for affected companies
        conn.execute(
            text(
                """
                DELETE FROM company_industries WHERE source_id IN (
                    SELECT source_id
                    FROM staging_company_industries
                    WHERE run_id = :run_id
                )
                """
            ),
            {"run_id": run_id},
        )

        conn.execute(
            text(
                """
                INSERT INTO company_industries (source_id, scheme, code, run_id)
                SELECT source_id, scheme, code, run_id
                FROM staging_company_industries
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        )

        # Replace relations for affected companies
        conn.execute(
            text(
                """
                DELETE FROM company_relations WHERE source_id IN (
                    SELECT source_id
                    FROM staging_company_relations
                    WHERE run_id = :run_id
                )
                """
            ),
            {"run_id": run_id},
        )

        conn.execute(
            text(
                """
                INSERT INTO company_relations (
                    source_id,
                    related_source_id,
                    relation_type,
                    description,
                    run_id
                )
                SELECT
                    source_id,
                    related_source_id,
                    relation_type,
                    description,
                    run_id
                FROM staging_company_relations
                WHERE run_id = :run_id
                """
            ),
            {"run_id": run_id},
        )
