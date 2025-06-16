import sys
import os
import types
from fastapi.testclient import TestClient
import spacy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "interpret_service"))

# Stubs before importing the service
sys.modules["openai"] = types.ModuleType("openai")
sys.modules["openai"].ChatCompletion = types.SimpleNamespace(
    create=lambda **kw: types.SimpleNamespace(
        choices=[types.SimpleNamespace(message={"content": '[{"subject":"s","verb":"v","object":"o","tags":["t"]}]'})]
    )
)

# Stub spacy.load to avoid large model requirement
spacy.load = lambda name: spacy.blank("en")

sys.modules["shared.redis_utils"] = types.SimpleNamespace(
    subscribe=lambda *a, **k: types.SimpleNamespace(get_message=lambda timeout=None: None),
    publish=lambda *a, **k: None,
)

sys.modules["interpret_worker"] = types.SimpleNamespace(listen_for_signals=lambda: None)

os.environ["INTERPRET_SKIP_THREADS"] = "1"
from interpret_service import main

client = TestClient(main.app)


def test_interpret_route():
    main.OPENAI_API_KEY = "test"
    resp = client.post(
        "/interpret",
        json={
            "lines": [
                {
                    "sentence": "Pressure is stable",
                    "timestamp": "t",
                    "source": "s",
                    "well_id": "w",
                }
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["subject"] == "s"
    assert data[0]["verb"] == "v"
    assert data[0]["object"] == "o"
    assert data[0]["tags"] == ["t"]
