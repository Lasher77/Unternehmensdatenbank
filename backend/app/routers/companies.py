from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..db import get_db
from ..schemas.company import (
    Company,
    CompanyDetailResponse,
    Event,
    IndustryCode,
    Person,
)

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/{source_id}", response_model=CompanyDetailResponse)
def get_company(
    source_id: str, db: Connection = Depends(get_db)
) -> CompanyDetailResponse:
    row = (
        db.execute(
            text(
                """
            SELECT source_id, raw_name, legal_form, name_norm,
                   COALESCE(email, data->>'email') AS email,
                   COALESCE(website, data->>'website') AS website,
                   COALESCE(phone, data->>'phone') AS phone,
                   COALESCE(
                       revenue,
                       CASE
                           WHEN NULLIF(btrim(data->>'revenue'), '') ~ '^[-+]?[0-9]+(\\.[0-9]+)?$'
                           THEN (data->>'revenue')::double precision
                           ELSE NULL
                       END
                   ) AS revenue,
                   street, postal_code, city, state, country, lat, lng,
                   register_id, register_city, register_country,
                   register_unique_key, status, terminated
            FROM companies
            WHERE source_id = :source_id
            """
            ),
            {"source_id": source_id},
        )
        .mappings()
        .one_or_none()
    )

    if row is None:
        raise HTTPException(status_code=404, detail="company not found")

    company_data = dict(row)
    company_data["name"] = company_data.pop("name_norm")
    company = Company(**company_data)

    event_rows = (
        db.execute(
            text(
                """
            SELECT event_id, event_date, event_type, description
            FROM events
            WHERE source_id = :source_id
            ORDER BY event_date
            """
            ),
            {"source_id": source_id},
        )
        .mappings()
        .all()
    )
    events = [
        Event(
            **{
                **dict(er),
                "event_date": (
                    er["event_date"].isoformat() if er["event_date"] else None
                ),
            }
        )
        for er in event_rows
    ]

    person_rows = (
        db.execute(
            text(
                """
            SELECT p.source_person_id, p.first_name, p.last_name, p.birth_date,
                   cpr.role_name, cpr.role_type, cpr.role_date
            FROM company_person_roles cpr
            JOIN persons p ON p.person_id = cpr.person_id
            WHERE cpr.source_id = :source_id
            ORDER BY p.source_person_id, cpr.role_date
            """
            ),
            {"source_id": source_id},
        )
        .mappings()
        .all()
    )
    persons_dict: dict[str, dict] = {}
    for pr in person_rows:
        pid = pr["source_person_id"]
        if pid not in persons_dict:
            persons_dict[pid] = {
                "source_person_id": pid,
                "first_name": pr["first_name"],
                "last_name": pr["last_name"],
                "birth_date": (
                    pr["birth_date"].isoformat() if pr["birth_date"] else None
                ),
                "roles": [],
            }
        persons_dict[pid]["roles"].append(
            {
                "role_name": pr["role_name"],
                "role_type": pr["role_type"],
                "role_date": pr["role_date"].isoformat() if pr["role_date"] else None,
            }
        )
    persons = [Person(**data) for data in persons_dict.values()]

    industry_rows = (
        db.execute(
            text(
                """
            SELECT scheme, code
            FROM company_industries
            WHERE source_id = :source_id
            ORDER BY scheme, code
            """
            ),
            {"source_id": source_id},
        )
        .mappings()
        .all()
    )
    industry_codes = [IndustryCode(**dict(ir)) for ir in industry_rows]

    return CompanyDetailResponse(
        company=company, events=events, persons=persons, industry_codes=industry_codes
    )
