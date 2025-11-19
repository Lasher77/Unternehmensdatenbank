import sys
from pathlib import Path

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.main import app


def test_salesforce_match_company_options_does_not_require_auth() -> None:
    client = TestClient(app)

    response = client.options("/api/salesforce/match-company")

    assert response.status_code == 200
