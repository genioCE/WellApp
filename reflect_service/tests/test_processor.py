import os
import sys

import types
import importlib

dummy_psycopg2 = types.ModuleType("psycopg2")
dummy_psycopg2.extensions = types.SimpleNamespace(connection=object)
sys.modules["psycopg2"] = dummy_psycopg2

if isinstance(sys.modules.get("pandas"), types.SimpleNamespace):
    del sys.modules["pandas"]
pd = importlib.import_module("pandas")

# Stub psycopg2 for offline testing
dummy_psycopg2 = types.ModuleType("psycopg2")
dummy_psycopg2.extras = types.SimpleNamespace(execute_batch=lambda *a, **k: None)
dummy_psycopg2.extensions = types.SimpleNamespace(connection=object)
sys.modules["psycopg2"] = dummy_psycopg2

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

# Stub psycopg2 to avoid postgres dependency
dummy_psycopg2 = types.ModuleType("psycopg2")
dummy_psycopg2.connect = lambda *a, **k: None
dummy_psycopg2.extensions = types.SimpleNamespace(connection=object, cursor=object)
sys.modules["psycopg2"] = dummy_psycopg2
sys.modules["psycopg2.extras"] = types.SimpleNamespace(
    execute_batch=lambda *a, **k: None
)

from reflect_service.processor import flag_anomalies, contains_keywords, KEYWORDS


def test_flag_anomalies_detects_spike():
    df = pd.DataFrame(
        {
            "pressure": [10, 10, 10, 10, 50],
            "flow_rate": [1, 1, 1, 1, 5],
        }
    )
    result = flag_anomalies(df)
    assert bool(result["anomaly"].iloc[-1]) is True
    assert bool(result["anomaly"].iloc[0]) is False


def test_contains_keywords():
    assert contains_keywords("Permit granted for drilling", KEYWORDS)
    assert not contains_keywords("Routine maintenance check", KEYWORDS)
