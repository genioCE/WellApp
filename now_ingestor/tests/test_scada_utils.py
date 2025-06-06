import sys
import types
import os

# Ensure project root on path for module imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

sys.modules['pandas'] = types.SimpleNamespace(Series=dict)
from now_ingestor.scada_utils import parse_scada_timestamp, row_to_memory
import pandas as pd


def test_parse_scada_timestamp():
    assert parse_scada_timestamp("05/07/2024 00:00-01:00") == "2024-05-07T00:00:00Z"


def test_row_to_memory():
    row = pd.Series({
        "DateTime": "05/07/2024 00:00-01:00",
        "diff_pressure_inH20": 1.0,
        "static_pressure_psia": 2.0,
        "temperature_degF": 3.0,
        "volume_mcf": 4.0,
        "flow_rate_mcf_day": 5.0,
        "energy_mmbtu": 6.0,
        "flow_time_pct": 7.0,
        "alarms": "none",
    })
    mem = row_to_memory(row)
    assert mem["source"] == "scada"
    assert mem["signal"]["flow_rate_mcf_day"] == 5.0
    assert mem["timestamp"] == "2024-05-07T00:00:00Z"
