"""Celery tasks for ingestion of NDJSON exports."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Any, TypedDict, Union

from sqlalchemy import MetaData, Table, func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

from .celery_app import celery_app
from ..db import engine
from ..opensearch_client import ensure_companies_index, get_opensearch, index_companies
from ..schemas.company import _normalize_optional_bool
from ..utils.country_normalization import normalize_country_code

BATCH_ERROR_SIZE = 100

logger = logging.getLogger(__name__)


metadata = MetaData()
companies_table = Table("companies", metadata, autoload_with=engine)


@dataclass
class IngestionError:
    """Simple container for a single ingestion failure."""

    run_id: int
    file_name: str
    error_code: str
    error_message: str
    raw_excerpt: str | None = None
    source_id: str | None = None
    line_number: int | None = None


class ImportRunResult(TypedDict, total=False):
    s3_key: str
    run_id: int
    summary: dict[str, int]
    finished_at: str


def _ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _extract_contact_details(extras: list[Any]) -> tuple[str | None, str | None, str | None]:
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


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_source_id(obj: dict[str, Any]) -> str:
    source_id = obj.get("id")
    if not source_id:
        raise ValueError("MISSING_SOURCE_ID")
    return str(source_id)


def map_company_payload(obj: dict[str, Any]) -> dict[str, Any]:
    name_data = _ensure_dict(obj.get("name"))
    address_data = _ensure_dict(obj.get("address"))
    register_data = _ensure_dict(obj.get("register"))
    extras_data = _ensure_list(obj.get("extras"))
    financials_data = _ensure_dict(obj.get("financials"))
    contact_data = _ensure_dict(obj.get("contact"))

    email, website, phone = _extract_contact_details(extras_data)
    if not email:
        email = contact_data.get("email")
    if not website:
        website = contact_data.get("website")
    if not phone:
        phone = contact_data.get("phone")

    return {
        "source_id": extract_source_id(obj),
        "raw_name": obj.get("rawName"),
        "legal_form": name_data.get("legalForm"),
        "name_norm": name_data.get("name"),
        "street": address_data.get("street"),
        "postal_code": address_data.get("postalCode"),
        "city": address_data.get("city"),
        "state": address_data.get("state"),
        "country": normalize_country_code(address_data.get("country")),
        "lat": _safe_float(address_data.get("lat")),
        "lng": _safe_float(address_data.get("lng")),
        "register_id": register_data.get("id"),
        "register_city": register_data.get("city"),
        "register_country": normalize_country_code(register_data.get("country")),
        "register_unique_key": register_data.get("uniqueKey"),
        "status": obj.get("status"),
        "terminated": _normalize_optional_bool(obj.get("terminated")),
        "email": email,
        "website": website,
        "phone": phone,
        "revenue": _extract_revenue(financials_data),
        "data": json.dumps(obj),
    }


def _insert_errors(conn, errors: list[IngestionError]) -> None:
    if not errors:
        return
    conn.execute(
        text(
            """
            INSERT INTO ingestion_errors (
                run_id,
                source_id,
                line_number,
                file_name,
                error_code,
                error_message,
                raw_excerpt
            ) VALUES (
                :run_id,
                :source_id,
                :line_number,
                :file_name,
                :error_code,
                :error_message,
                :raw_excerpt
            )
            """
        ),
        [error.__dict__ for error in errors],
    )


def _upsert_company(conn, company: dict[str, Any], run_id: int) -> None:
    insert_stmt = insert(companies_table).values(
        source_id=company["source_id"],
        raw_name=company.get("raw_name"),
        legal_form=company.get("legal_form"),
        name_norm=company.get("name_norm"),
        street=company.get("street"),
        postal_code=company.get("postal_code"),
        city=company.get("city"),
        state=company.get("state"),
        country=company.get("country") or "DE",
        lat=company.get("lat"),
        lng=company.get("lng"),
        register_id=company.get("register_id"),
        register_city=company.get("register_city"),
        register_country=company.get("register_country"),
        register_unique_key=company.get("register_unique_key"),
        status=company.get("status"),
        terminated=company.get("terminated"),
        data=company.get("data"),
        seen_in_run=run_id,
        email=(company.get("email") or "").strip() or None,
        website=(company.get("website") or "").strip() or None,
        phone=(company.get("phone") or "").strip() or None,
        revenue=company.get("revenue"),
        updated_at=func.now(),
    )

    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[companies_table.c.source_id],
        set_={
            "raw_name": insert_stmt.excluded.raw_name,
            "legal_form": insert_stmt.excluded.legal_form,
            "name_norm": insert_stmt.excluded.name_norm,
            "street": insert_stmt.excluded.street,
            "postal_code": insert_stmt.excluded.postal_code,
            "city": insert_stmt.excluded.city,
            "state": insert_stmt.excluded.state,
            "country": insert_stmt.excluded.country,
            "lat": insert_stmt.excluded.lat,
            "lng": insert_stmt.excluded.lng,
            "register_id": insert_stmt.excluded.register_id,
            "register_city": insert_stmt.excluded.register_city,
            "register_country": insert_stmt.excluded.register_country,
            "register_unique_key": insert_stmt.excluded.register_unique_key,
            "status": insert_stmt.excluded.status,
            "terminated": insert_stmt.excluded.terminated,
            "data": insert_stmt.excluded.data,
            "seen_in_run": insert_stmt.excluded.seen_in_run,
            "email": insert_stmt.excluded.email,
            "website": insert_stmt.excluded.website,
            "phone": insert_stmt.excluded.phone,
            "revenue": insert_stmt.excluded.revenue,
            "updated_at": func.now(),
        },
    )

    conn.execute(upsert_stmt)


@celery_app.task(bind=True)
def run_import(self, s3_key: str, label: str | None = None) -> ImportRunResult:
    file_name = label or Path(s3_key).name
    with open(s3_key, "r", encoding="utf-8") as fh:
        total_entries = sum(1 for line in fh if line.strip())
        fh.seek(0)

        with engine.begin() as conn:
            run_id = conn.execute(
                text(
                    "INSERT INTO ingestion_run (source, notes) VALUES (:src, :notes) "
                    "RETURNING run_id"
                ),
                {"src": "file", "notes": file_name},
            ).scalar_one()

        logger.info("Started import run", extra={"run_id": run_id, "file": file_name, "total": total_entries})

        errors: list[IngestionError] = []
        seen_source_ids: set[str] = set()
        successful_source_ids: list[str] = []
        processed = 0
        successful_records = 0
        error_records = 0

        with engine.connect() as conn:
            for line_number, line in enumerate(fh, start=1):
                raw_line = line.strip()
                if not raw_line:
                    continue

                processed += 1
                source_id: str | None = None
                try:
                    try:
                        obj = json.loads(raw_line)
                    except JSONDecodeError as exc:
                        error_records += 1
                        errors.append(
                            IngestionError(
                                run_id=run_id,
                                source_id=None,
                                line_number=line_number,
                                file_name=file_name,
                                error_code="JSON_PARSE_ERROR",
                                error_message=str(exc),
                                raw_excerpt=raw_line[:500],
                            )
                        )
                        if len(errors) >= BATCH_ERROR_SIZE:
                            with conn.begin():
                                _insert_errors(conn, errors)
                            errors = []
                        continue

                    try:
                        source_id = extract_source_id(obj)
                    except ValueError:
                        error_records += 1
                        errors.append(
                            IngestionError(
                                run_id=run_id,
                                source_id=None,
                                line_number=line_number,
                                file_name=file_name,
                                error_code="MISSING_SOURCE_ID",
                                error_message="Datensatz ohne source_id",
                                raw_excerpt=raw_line[:500],
                            )
                        )
                        if len(errors) >= BATCH_ERROR_SIZE:
                            with conn.begin():
                                _insert_errors(conn, errors)
                            errors = []
                        continue

                    if source_id in seen_source_ids:
                        # Ignore duplicate source IDs within the same import run to keep
                        # processing the remaining entries without raising ingestion
                        # errors for repeated records.
                        continue

                    try:
                        company_payload = map_company_payload(obj)
                    except Exception as exc:  # noqa: BLE001
                        error_records += 1
                        errors.append(
                            IngestionError(
                                run_id=run_id,
                                source_id=source_id,
                                line_number=line_number,
                                file_name=file_name,
                                error_code="MAPPING_ERROR",
                                error_message=str(exc),
                                raw_excerpt=raw_line[:500],
                            )
                        )
                        if len(errors) >= BATCH_ERROR_SIZE:
                            with conn.begin():
                                _insert_errors(conn, errors)
                            errors = []
                        continue

                    try:
                        with conn.begin():
                            _upsert_company(conn, company_payload, run_id)
                    except SQLAlchemyError as exc:
                        error_records += 1
                        errors.append(
                            IngestionError(
                                run_id=run_id,
                                source_id=source_id,
                                line_number=line_number,
                                file_name=file_name,
                                error_code="UPSERT_ERROR",
                                error_message=str(exc.orig) if hasattr(exc, "orig") else str(exc),
                                raw_excerpt=raw_line[:500],
                            )
                        )
                        if len(errors) >= BATCH_ERROR_SIZE:
                            with conn.begin():
                                _insert_errors(conn, errors)
                            errors = []
                        continue
                except Exception as exc:  # noqa: BLE001
                    error_records += 1
                    errors.append(
                        IngestionError(
                            run_id=run_id,
                            source_id=source_id,
                            line_number=line_number,
                            file_name=file_name,
                            error_code="UNEXPECTED_ERROR",
                            error_message=str(exc),
                            raw_excerpt=raw_line[:500],
                        )
                    )
                    if len(errors) >= BATCH_ERROR_SIZE:
                        with conn.begin():
                            _insert_errors(conn, errors)
                        errors = []
                    continue

                seen_source_ids.add(source_id)
                successful_records += 1
                successful_source_ids.append(source_id)

                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": processed,
                        "total": total_entries,
                        "percent": int(processed * 100 / total_entries) if total_entries else 0,
                    },
                )

            if errors:
                with conn.begin():
                    _insert_errors(conn, errors)

            companies: list[dict[str, Any]] = []
            if successful_source_ids:
                with conn.begin():
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
                                WHERE source_id = ANY(:source_ids)
                                """
                            ),
                            {"source_ids": successful_source_ids},
                        )
                        .mappings()
                        .all()
                    )

        try:
            if companies:
                client = get_opensearch()
                ensure_companies_index(client)
                index_companies(client, companies)
        except Exception:
            pass

    finished_at = datetime.now(timezone.utc)
    with engine.begin() as conn:
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
                "summary": json.dumps(
                    {
                        "companies": successful_records,
                        "errors": error_records,
                    }
                ),
                "run_id": run_id,
            },
        )

    logger.info(
        "Finished import run",
        extra={
            "run_id": run_id,
            "file": file_name,
            "processed": processed,
            "successful": successful_records,
            "errors": error_records,
        },
    )

    return {
        "status": "completed",
        "run_id": run_id,
        "label": file_name,
        "s3_key": s3_key,
        "file": s3_key,
        "total_records": processed,
        "successful_records": successful_records,
        "error_records": error_records,
    }


@celery_app.task
def cleanup_import_file(result: Union[ImportRunResult, str]) -> Union[ImportRunResult, str]:
    if isinstance(result, str):
        path = Path(result)
    else:
        path = Path(result["s3_key"]) if "s3_key" in result else Path(result.get("file", ""))

    try:
        path.unlink()
    except FileNotFoundError:
        pass

    return result
