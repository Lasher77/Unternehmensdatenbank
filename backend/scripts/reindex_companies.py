from sqlalchemy import text

from backend.app.db import engine
from backend.app.opensearch_client import (
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
