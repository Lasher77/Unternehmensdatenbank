import json
from pathlib import Path

from sqlalchemy import text

from .celery_app import celery_app
from ..db import engine
from ..schemas.company import Company, Event
from ..utils.staging_loader import load_to_staging, promote_staging
from ..opensearch_client import (
    ensure_companies_index,
    get_opensearch,
    index_companies,
)

BATCH_SIZE = 1000


@celery_app.task(bind=True)
def run_import(self, s3_key: str) -> str:
    """Import companies from an NDJSON file.

    The ``s3_key`` parameter is treated as a local file path. Each line is
    parsed according to the NorthData export structure and relevant fields are
    written into the staging tables.
    """

    with open(s3_key, "r", encoding="utf-8") as fh:
        total_entries = sum(1 for line in fh if line.strip())
        fh.seek(0)

        rows: list[dict] = []
        processed = 0

        with engine.begin() as conn:
            run_id = conn.execute(
                text(
                    "INSERT INTO ingestion_run (source) VALUES (:src) "
                    "RETURNING run_id"
                ),
                {"src": "file"},
            ).scalar_one()

        def report_progress() -> None:
            if total_entries:
                percent = int(processed * 100 / total_entries)
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": processed,
                        "total": total_entries,
                        "percent": percent,
                    },
                )

        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)

            company = Company(
                source_id=data["id"],
                raw_name=data.get("rawName"),
                legal_form=data.get("name", {}).get("legalForm"),
                name=data.get("name", {}).get("name"),
                street=data.get("address", {}).get("street"),
                postal_code=data.get("address", {}).get("postalCode"),
                city=data.get("address", {}).get("city"),
                state=data.get("address", {}).get("state"),
                country=data.get("address", {}).get("country"),
                lat=data.get("address", {}).get("lat"),
                lng=data.get("address", {}).get("lng"),
                register_id=data.get("register", {}).get("id"),
                register_city=data.get("register", {}).get("city"),
                register_country=data.get("register", {}).get("country"),
                register_unique_key=data.get("register", {}).get("uniqueKey"),
                status=data.get("status"),
                terminated=data.get("terminated"),
            )

            events = [
                Event(
                    event_date=item.get("date"),
                    event_type=item.get("type"),
                    description=item.get("description"),
                ).model_dump()
                for item in data.get("events", {}).get("items", [])
            ]

            persons: list[dict] = []
            person_roles: list[dict] = []
            for rp in data.get("relatedPersons", {}).get("items", []):
                p = rp.get("person", {})
                source_person_id = p.get("id")
                if not source_person_id:
                    continue
                persons.append({"source_person_id": source_person_id, "data": p})
                description = rp.get("description")
                for role in rp.get("roles", []):
                    demotion = role.get("demotion")
                    person_roles.append(
                        {
                            "source_id": data["id"],
                            "source_person_id": source_person_id,
                            "role_name": role.get("name"),
                            "role_type": role.get("type"),
                            "role_date": role.get("date"),
                            "description": description,
                            "demotion": demotion,
                        }
                    )

            industries: list[dict] = []
            for scheme, codes in data.get("segmentCodes", {}).items():
                for code in codes:
                    industries.append(
                        {
                            "source_id": data["id"],
                            "scheme": scheme,
                            "code": code,
                        }
                    )

            relations: list[dict] = []
            for rel in data.get("relatedCompanies", {}).get("items", []):
                related_company = rel.get("company", {})
                related_source_id = related_company.get("id")
                if not related_source_id:
                    continue

                rel_roles = rel.get("roles") or [None]
                for role in rel_roles:
                    relation_type = None
                    if role:
                        relation_type = role.get("type") or role.get("name")

                    relations.append(
                        {
                            "source_id": data["id"],
                            "related_source_id": related_source_id,
                            "relation_type": relation_type,
                            "description": rel.get("description"),
                        }
                    )

            rows.append(
                {
                    "company": company.model_dump(),
                    "events": events,
                    "persons": persons,
                    "roles": person_roles,
                    "industries": industries,
                    "relations": relations,
                }
            )
            processed += 1

            if len(rows) >= BATCH_SIZE:
                load_to_staging(rows, run_id)
                rows = []
                report_progress()

        if rows:
            load_to_staging(rows, run_id)
            rows = []
            report_progress()

    finalize_import.delay(run_id)
    return s3_key


@celery_app.task
def finalize_import(run_id: int) -> int:
    """Promote staging data for ``run_id`` into the main tables."""

    promote_staging(run_id)

    with engine.begin() as conn:
        companies = (
            conn.execute(
                text(
                    """
                SELECT
                    source_id,
                    name_norm AS name,
                    state,
                    city,
                    postal_code,
                    status,
                    legal_form,
                    lat,
                    lng
                FROM companies
                WHERE seen_in_run = :run_id
                """
                ),
                {"run_id": run_id},
            )
            .mappings()
            .all()
        )

    client = get_opensearch()
    ensure_companies_index(client)
    index_companies(client, companies)

    return run_id


@celery_app.task
def cleanup_import_file(file_path: str) -> str:
    """Delete a temporary import file once it is no longer needed."""

    path = Path(file_path)
    try:
        path.unlink()
    except FileNotFoundError:
        pass

    return file_path
