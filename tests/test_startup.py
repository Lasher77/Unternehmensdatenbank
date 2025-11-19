import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError

import backend.app.main as main
from backend.app.main import app


class DummyIndices:
    def __init__(self) -> None:
        self._exists = False

    def exists(self, index: str) -> bool:  # pragma: no cover - simple stub
        return self._exists

    def create(self, index: str, body: dict) -> None:  # pragma: no cover - simple stub
        self._exists = True


class DummyOSClient:
    def __init__(self) -> None:
        self.indices = DummyIndices()


def test_startup_creates_companies_index(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyOSClient()
    monkeypatch.setattr(main, "get_opensearch", lambda: dummy)
    with TestClient(app):
        pass
    assert dummy.indices.exists(index="companies")


def test_startup_logs_when_opensearch_unavailable(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    dummy = DummyOSClient()
    monkeypatch.setattr(main, "get_opensearch", lambda: dummy)

    def _raise(_: DummyOSClient) -> None:
        raise OpenSearchConnectionError("N/A", "boom", Exception("boom"))

    monkeypatch.setattr(main, "ensure_companies_index", _raise)

    with caplog.at_level("WARNING"):
        with TestClient(app):
            pass

    assert "Skipping OpenSearch index initialization" in caplog.text
