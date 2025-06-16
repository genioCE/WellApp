import os
import sys
import types

from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)


dummy_requests = types.ModuleType("requests")
dummy_requests.post = lambda *args, **kwargs: None
sys.modules["requests"] = dummy_requests

from now_file_ingestor.main import app


def _prepare_app():
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()


class DummyRedis:
    def __init__(self):
        self.published = []

    def publish(self, channel: str, message: str) -> None:
        self.published.append((channel, message))


def test_ingest_file(tmp_path, monkeypatch):
    _prepare_app()
    dummy = DummyRedis()
    monkeypatch.setattr("now_file_ingestor.main.redis_client", dummy)
    monkeypatch.setattr("now_file_ingestor.main.RAW_DATA_ROOT", str(tmp_path))

    client = TestClient(app)
    resp = client.post(
        "/ingest",
        data={"well_id": "w1"},
        files={"file": ("data.csv", "x,y\n1,2", "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert os.path.exists(data["file_path"])
    assert dummy.published
    assert dummy.published[0][0] == "file_ingest"
