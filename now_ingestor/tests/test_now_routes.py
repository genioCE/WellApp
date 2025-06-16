import sys
import os
import types
from fastapi.testclient import TestClient

# Ensure project root on path for module imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)


class DummyPool:
    def __init__(self, *args, **kwargs):
        pass

    def getconn(self):
        return None

    def putconn(self, conn):
        pass


dummy_psycopg2 = types.ModuleType("psycopg2")
dummy_psycopg2.pool = types.SimpleNamespace(SimpleConnectionPool=DummyPool)
sys.modules["psycopg2"] = dummy_psycopg2
sys.modules["psycopg2.pool"] = types.SimpleNamespace(SimpleConnectionPool=DummyPool)

dummy_redis_utils = types.ModuleType("shared.redis_utils")
dummy_redis_utils.publish = lambda *args, **kwargs: None
sys.modules["shared.redis_utils"] = dummy_redis_utils

from now_ingestor.main import app


def _prepare_app():
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()


def test_upload_scada(tmp_path, monkeypatch):
    _prepare_app()
    messages = {}

    def fake_publish(channel: str, payload: dict) -> None:
        messages["channel"] = channel
        messages["payload"] = payload

    monkeypatch.setattr("now_ingestor.main.publish", fake_publish)
    monkeypatch.setattr("now_ingestor.main.DATA_ROOT", str(tmp_path))

    client = TestClient(app)
    content = "a,b\n1,2"
    response = client.post(
        "/now/scada",
        data={"well_id": "well1"},
        files={"file": ("data.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    assert messages["payload"]["event"] == "scada_ingest_ready"
    saved_path = messages["payload"]["file_path"]
    assert os.path.exists(saved_path)
    assert messages["payload"]["well_id"] == "well1"
    assert messages["payload"]["source"] == "scada"


def test_upload_wellfile(tmp_path, monkeypatch):
    _prepare_app()
    messages = {}

    def fake_publish(channel: str, payload: dict) -> None:
        messages["channel"] = channel
        messages["payload"] = payload

    monkeypatch.setattr("now_ingestor.main.publish", fake_publish)
    monkeypatch.setattr("now_ingestor.main.DATA_ROOT", str(tmp_path))

    client = TestClient(app)
    pdf_bytes = b"%PDF-1.4\n%test"
    response = client.post(
        "/now/wellfile",
        data={"well_id": "well1"},
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert messages["payload"]["event"] == "wellfile_ingest_ready"
    saved_path = messages["payload"]["file_path"]
    assert os.path.exists(saved_path)
    assert messages["payload"]["well_id"] == "well1"
    assert messages["payload"]["source"] == "wellfile"
