import sys
import os
from types import SimpleNamespace
import types

dummy_openai = types.ModuleType("openai")
dummy_openai.ChatCompletion = types.SimpleNamespace(create=lambda **kw: None)
dummy_openai.__spec__ = types.SimpleNamespace()
sys.modules["openai"] = dummy_openai

SERVICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, SERVICE_DIR)

from main import prepare_entries


def test_prepare_entries():
    point = SimpleNamespace(
        id="123",
        payload={
            "well_id": "w1",
            "source": "scada",
            "timestamp": "2024-01-01T00:00:00Z",
            "text": "hello",
            "noun_phrases": ["hello"],
            "anomaly": True,
            "loop_stage": "truth",
            "source_file": "f.txt",
        },
    )
    entries = prepare_entries([point])
    assert len(entries) == 1
    entry = entries[0]
    assert entry[1] == "w1"
    assert entry[2] == "scada"
    assert entry[3] == "2024-01-01T00:00:00Z"
    assert entry[4] == "hello"
    assert entry[5] == ["hello"]
    assert entry[6] is True
    assert entry[7] == "123"
    assert entry[8] == "truth"
