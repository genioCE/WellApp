import sys
import types
import os
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

# Avoid heavy imports for sentence_transformers
sys.modules["sentence_transformers"] = types.SimpleNamespace(
    SentenceTransformer=lambda *args, **kwargs: None
)
sys.modules["shared.redis_utils"] = types.SimpleNamespace(
    subscribe=lambda *a, **k: types.SimpleNamespace(listen=lambda: []),
    publish=lambda *a, **k: None,
)

from replay_memory_service import main

client = TestClient(main.app)


def test_search_memory():
    # Mock model.encode and qdrant_client.search
    class Enc:
        def __init__(self, v):
            self.v = v

        def tolist(self):
            return self.v

    main.model = types.SimpleNamespace(encode=lambda x: Enc([0.1, 0.2]))
    main.qdrant_client = types.SimpleNamespace(
        search=lambda **kwargs: [
            types.SimpleNamespace(
                payload={
                    "text": "test",
                    "source": "s",
                    "timestamp": "t",
                    "anomaly": False,
                },
                id="1",
            )
        ]
    )
    resp = client.get("/replay/search", params={"query": "q", "well_id": "w"})
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["vector_id"] == "1"


def test_replay_timeline():
    async def fetch(query, *params):
        return [
            {
                "text": "t",
                "timestamp_or_page": "p",
                "anomaly_or_importance": False,
                "loop_stage": "ls",
                "vector_id": "v",
            }
        ]

    class Conn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def fetch(self, query, *params):
            return await fetch(query, *params)

    class Pool:
        def acquire(self):
            return Conn()

    main.pg_pool = Pool()
    resp = client.get("/replay/timeline", params={"well_id": "w"})
    assert resp.status_code == 200
    assert resp.json()[0]["vector_id"] == "v"


def test_chat_endpoint(tmp_path):
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

    class Dummy:
        choices = [types.SimpleNamespace(message={"content": "answer"})]

    main.OPENAI_API_KEY = "test"
    main.openai = types.SimpleNamespace(
        ChatCompletion=types.SimpleNamespace(create=lambda **kw: Dummy())
    )

    resp = client.post(
        "/chat",
        json={"well_id": "w", "question": "q", "persona": "operator"},
    )
    assert resp.status_code == 200
    assert resp.json()["answer"] == "answer"
