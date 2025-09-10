import json

from .celery_app import celery_app
from ..schemas.company import Company, Event
from ..utils.staging_loader import load_to_staging


@celery_app.task
def run_import(s3_key: str) -> str:
    """Import companies from an NDJSON file.

    The ``s3_key`` parameter is treated as a local file path. Each line is
    parsed according to the NorthData export structure and relevant fields are
    written into the staging tables.
    """

    rows: list[dict] = []
    with open(s3_key, "r", encoding="utf-8") as fh:
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

            rows.append({"company": company.model_dump(), "events": events})

    load_to_staging(rows)
    return s3_key
