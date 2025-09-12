from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..db import get_db
from ..schemas.company import Company, CompanyDetailResponse, Event

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/{source_id}", response_model=CompanyDetailResponse)
def get_company(
    source_id: str, db: Connection = Depends(get_db)
) -> CompanyDetailResponse:
    row = db.execute(
        text(
            """
            SELECT source_id, raw_name, legal_form, name_norm, street,
                   postal_code, city, state, country, lat, lng,
                   register_id, register_city, register_country,
                   register_unique_key, status, terminated
            FROM companies
            WHERE source_id = :source_id
            """
        ),
        {"source_id": source_id},
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="company not found")

    company_data = dict(row)
    company_data["name"] = company_data.pop("name_norm")
    company = Company(**company_data)

    event_rows = db.execute(
        text(
            """
            SELECT event_id, event_date, event_type, description
            FROM events
            WHERE source_id = :source_id
            ORDER BY event_date
            """
        ),
        {"source_id": source_id},
    ).mappings().all()
    events = [
        Event(
            **{**dict(er), "event_date": er["event_date"].isoformat() if er["event_date"] else None}
        )
        for er in event_rows
    ]

    return CompanyDetailResponse(company=company, events=events)
