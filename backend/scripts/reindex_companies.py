import sys
from pathlib import Path

from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db import engine
from app.opensearch_client import (
    ensure_companies_index,
    get_opensearch,
    index_companies,
)


QUERY = """
    SELECT
        source_id,
        name_norm AS name,
        state,
        city,
        postal_code,
        street,
        country,
        COALESCE(email, data->>'email') AS email,
        COALESCE(website, data->>'website') AS website,
        COALESCE(phone, data->>'phone') AS phone,
        register_id,
        COALESCE(data->>'vat_id', data->>'vatId') AS vat_id,
        status,
        legal_form,
        lat,
        lng
    FROM companies
"""


def main() -> None:
    with engine.begin() as conn:
        companies = conn.execute(text(QUERY)).mappings().all()

    client = get_opensearch()
    ensure_companies_index(client)
    index_companies(client, companies)


if __name__ == "__main__":
    main()
