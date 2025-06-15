import io
from datetime import timedelta
from typing import Iterable

import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "flow_rate", "pressure", "temperature", "volume"}


def parse_scada_csv(contents: bytes) -> pd.DataFrame:
    """Parse SCADA CSV bytes and ensure required columns are present."""
    df = pd.read_csv(io.BytesIO(contents))
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    return df


def validate_hourly_sequence(timestamps: Iterable) -> None:
    """Validate timestamps are hourly and sequential."""
    times = pd.to_datetime(list(timestamps))
    diffs = times.diff().dropna()
    if not (diffs == timedelta(hours=1)).all():
        raise ValueError("Timestamps must be hourly and sequential")
