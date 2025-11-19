import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict, Union

from sqlalchemy import text

from .celery_app import celery_app
from ..db import engine
from ..schemas.company import Company, Event
from ..utils.date_normalization import normalize_birth_date
from ..utils.staging_loader import load_to_staging, promote_staging
from ..opensearch_client import (
    ensure_companies_index,
    get_opensearch,
    index_companies,
)

BATCH_SIZE = 1000


def _ensure_dict(value: Any) -> dict[str, Any]:
    """Return ``value`` when it is a ``dict``, otherwise an empty mapping."""

    if isinstance(value, dict):
        return value
    return {}


def _ensure_list(value: Any) -> list[Any]:
    """Return ``value`` when it is a list, otherwise an empty list."""

    if isinstance(value, list):
        return value
    return []


def _extract_contact_details(extras: list[Any]) -> tuple[str | None, str | None, str | None]:
    """Return email, website and phone values from ``extras`` entries if present."""

    email: str | None = None
    website: str | None = None
    phone: str | None = None

    for extra in extras:
        if not isinstance(extra, dict):
            continue
        for item in _ensure_list(extra.get("items")):
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or "").lower()
            value = item.get("value")
            if not value:
                continue
            if email is None and item_id in {"email", "mail"}:
                email = value
            elif website is None and item_id in {"url", "website", "homepage"}:
                website = value
            elif phone is None and item_id in {"phone", "tel", "telephone"}:
                phone = value

    return email, website, phone


def _extract_revenue(financials: dict[str, Any]) -> float | None:
    """Return the revenue value from a ``financials`` block if available."""

    for item in _ensure_list(financials.get("items")):
        if not isinstance(item, dict):
            continue
        if item.get("id") != "Revenue":
            continue
        value = item.get("value")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


class ImportRunResult(TypedDict, total=False):
    s3_key: str
    run_id: int
    summary: dict[str, int]
    finished_at: str


@celery_app.task(bind=True)
def run_import(self, s3_key: str) -> ImportRunResult:
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

            source_id = data.get("id")
            if not source_id:
                raise ValueError("Einträge ohne id können nicht importiert werden")

            name_data = _ensure_dict(data.get("name"))
            address_data = _ensure_dict(data.get("address"))
            register_data = _ensure_dict(data.get("register"))
            extras_data = _ensure_list(data.get("extras"))
            financials_data = _ensure_dict(data.get("financials"))
            contact_data = _ensure_dict(data.get("contact"))
            events_data = _ensure_dict(data.get("events"))
            related_persons_data = _ensure_dict(data.get("relatedPersons"))
            related_companies_data = _ensure_dict(data.get("relatedCompanies"))
            segment_codes_data = _ensure_dict(data.get("segmentCodes"))

            email, website, phone = _extract_contact_details(extras_data)
            if not email:
                email = contact_data.get("email")
            if not website:
                website = contact_data.get("website")
            if not phone:
                phone = contact_data.get("phone")

            revenue = _extract_revenue(financials_data)

            company = Company(
                source_id=str(source_id),
                raw_name=data.get("rawName"),
                legal_form=name_data.get("legalForm"),
                name=name_data.get("name"),
                email=email,
                website=website,
                phone=phone,
                revenue=revenue,
                street=address_data.get("street"),
                postal_code=address_data.get("postalCode"),
                city=address_data.get("city"),
                state=address_data.get("state"),
                country=address_data.get("country"),
                lat=address_data.get("lat"),
                lng=address_data.get("lng"),
                register_id=register_data.get("id"),
                register_city=register_data.get("city"),
                register_country=register_data.get("country"),
                register_unique_key=register_data.get("uniqueKey"),
                status=data.get("status"),
                terminated=data.get("terminated"),
            )

            events = [
                Event(
                    event_date=item.get("date"),
                    event_type=item.get("type"),
                    description=item.get("description"),
                ).model_dump()
                for item in _ensure_list(events_data.get("items"))
            ]

            persons: list[dict] = []
            person_roles: list[dict] = []
            for rp in _ensure_list(related_persons_data.get("items")):
                if not isinstance(rp, dict):
                    continue

                p = _ensure_dict(rp.get("person"))
                source_person_id = p.get("id")
                if not source_person_id:
                    continue
                source_person_id = str(source_person_id)
                person_data = dict(p)
                raw_birth = person_data.get("birthDate")
                if isinstance(raw_birth, str):
                    normalized_birth = normalize_birth_date(raw_birth)
                elif raw_birth is not None:
                    normalized_birth = normalize_birth_date(str(raw_birth))
                else:
                    normalized_birth = None
                if normalized_birth is not None:
                    person_data["birthDate"] = normalized_birth
                elif "birthDate" in person_data or raw_birth is not None:
                    person_data["birthDate"] = None

                persons.append({"source_person_id": source_person_id, "data": person_data})
                description = rp.get("description")
                for role in _ensure_list(rp.get("roles")):
                    if not isinstance(role, dict):
                        continue
                    demotion = role.get("demotion")
                    person_roles.append(
                        {
                            "source_id": company.source_id,
                            "source_person_id": source_person_id,
                            "role_name": role.get("name"),
                            "role_type": role.get("type"),
                            "role_date": role.get("date"),
                            "description": description,
                            "demotion": demotion,
                        }
                    )

            industries: list[dict] = []
            for scheme, codes in segment_codes_data.items():
                if not isinstance(codes, list):
                    continue
                for code in codes:
                    industries.append(
                        {
                            "source_id": company.source_id,
                            "scheme": scheme,
                            "code": code,
                        }
                    )

            relations: list[dict] = []
            for rel in _ensure_list(related_companies_data.get("items")):
                if not isinstance(rel, dict):
                    continue
                related_company = _ensure_dict(rel.get("company"))
                related_source_id = related_company.get("id")
                if not related_source_id:
                    continue
                related_source_id = str(related_source_id)

                rel_roles = rel.get("roles")
                if not isinstance(rel_roles, list):
                    rel_roles = [None]

                for role in rel_roles:
                    relation_type = None
                    if isinstance(role, dict):
                        relation_type = role.get("type") or role.get("name")

                    relations.append(
                        {
                            "source_id": company.source_id,
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

    return {"s3_key": s3_key, "run_id": run_id}


@celery_app.task
def finalize_import(result: Union[ImportRunResult, int]) -> ImportRunResult:
    """Promote staging data for ``run_id`` into the main tables."""

    if isinstance(result, dict):
        run_id = result["run_id"]
        run_result: ImportRunResult = dict(result)
    else:
        run_id = int(result)
        run_result = {"run_id": run_id}

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

        table_queries = {
            "companies": "SELECT COUNT(*) FROM companies WHERE seen_in_run = :run_id",
            "events": "SELECT COUNT(*) FROM events WHERE run_id = :run_id",
            "company_person_roles": (
                "SELECT COUNT(*) FROM company_person_roles WHERE run_id = :run_id"
            ),
            "company_industries": (
                "SELECT COUNT(*) FROM company_industries WHERE run_id = :run_id"
            ),
            "company_relations": (
                "SELECT COUNT(*) FROM company_relations WHERE run_id = :run_id"
            ),
            "company_history": (
                "SELECT COUNT(*) FROM company_history WHERE run_id = :run_id"
            ),
        }

        summary: dict[str, int] = {}
        for table_name, query in table_queries.items():
            count = conn.execute(text(query), {"run_id": run_id}).scalar_one()
            summary[table_name] = int(count)

        finished_at = datetime.now(timezone.utc)
        conn.execute(
            text(
                """
                UPDATE ingestion_run
                SET finished_at = :finished_at,
                    summary = CAST(:summary AS jsonb)
                WHERE run_id = :run_id
                """
            ),
            {
                "finished_at": finished_at,
                "summary": json.dumps(summary),
                "run_id": run_id,
            },
        )

    client = get_opensearch()
    ensure_companies_index(client)
    index_companies(client, companies)

    run_result["summary"] = summary
    run_result["finished_at"] = finished_at.isoformat()
    return run_result


@celery_app.task
def cleanup_import_file(
    result: Union[ImportRunResult, str]
) -> Union[ImportRunResult, str]:
    """Delete a temporary import file once it is no longer needed."""

    if isinstance(result, str):
        path = Path(result)
    else:
        path = Path(result["s3_key"])

    try:
        path.unlink()
    except FileNotFoundError:
        pass

    return result
