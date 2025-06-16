import sys
import types
import os
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

# Lightweight mocks
sys.modules["sentence_transformers"] = types.SimpleNamespace(
    SentenceTransformer=lambda *args, **kwargs: None
)
sys.modules["openai"] = types.SimpleNamespace(
    ChatCompletion=types.SimpleNamespace(create=lambda **kw: None)
)
sys.modules["shared.redis_utils"] = types.SimpleNamespace(
    subscribe=lambda *a, **k: types.SimpleNamespace(listen=lambda: []),
    publish=lambda *a, **k: None,
)

from memory_replay_viewer_service import main

client = TestClient(main.app)


def test_chat_route():
    class Enc:
        def __init__(self, v):
            self.v = v

        def tolist(self):
            return self.v

    main.model = types.SimpleNamespace(encode=lambda x: Enc([0.1]))
    main.qdrant_client = types.SimpleNamespace(
        search=lambda **kwargs: [
            types.SimpleNamespace(payload={"text": "context"}, id="1")
        ]
    )
    main.OPENAI_API_KEY = "test"

    class Dummy:
        choices = [types.SimpleNamespace(message={"content": "answer"})]

    main.openai = types.SimpleNamespace(
        ChatCompletion=types.SimpleNamespace(create=lambda **kw: Dummy())
    )
    resp = client.post("/chat", params={"query": "q", "well_id": "w"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "answer"
