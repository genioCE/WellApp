import os
import sys
import types
import json
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

# Patch openai before importing the app
response_payload = [
    {
        "timestamp": "2024-01-01",
        "event": "pressure spike",
        "confirmed_cause": "pump failure",
        "next_question": "",
    }
]

sys.modules["openai"] = types.SimpleNamespace(
    ChatCompletion=types.SimpleNamespace(
        create=lambda **kwargs: types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message={"content": json.dumps(response_payload)}
                )
            ]
        )
    )
)

os.environ["OPENAI_API_KEY"] = "test"

from reflect_service.main import app

client = TestClient(app)


def test_reflect_endpoint():
    resp = client.post(
        "/reflect",
        json={"sentences": ["2024-01-01 pressure spike due to pump failure"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["confirmed_cause"] == "pump failure"
