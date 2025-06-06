from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
import pandas as pd


def parse_scada_timestamp(value: str) -> str:
    """Convert SCADA DateTime string to ISO 8601 UTC string."""
    base = value.split("-")[0].strip()
    dt = datetime.strptime(base, "%m/%d/%Y %H:%M")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def row_to_memory(row: pd.Series | Dict[str, Any]) -> Dict[str, Any]:
    """Convert a SCADA CSV row into a memory dict."""
    if isinstance(row, dict):
        row = pd.Series(row)

    ts_iso = parse_scada_timestamp(str(row["DateTime"]))

    signal = {
        "diff_pressure_inH20": float(row["diff_pressure_inH20"]),
        "static_pressure_psia": float(row["static_pressure_psia"]),
        "temperature_degF": float(row["temperature_degF"]),
        "volume_mcf": float(row["volume_mcf"]),
        "flow_rate_mcf_day": float(row["flow_rate_mcf_day"]),
        "energy_mmbtu": float(row["energy_mmbtu"]),
        "flow_time_pct": float(row["flow_time_pct"]),
        "alarms": str(row.get("alarms", "")),
    }

    memory = {
        "timestamp": ts_iso,
        "signal": signal,
        "source": "scada",
        "tags": ["scada", "automated", "sensor"],
        "content": f"SCADA reading flow={signal['flow_rate_mcf_day']} at {ts_iso}",
    }
    return memory
