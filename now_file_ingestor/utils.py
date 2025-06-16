import io
import os
import uuid
from datetime import datetime, timedelta
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


def classify_filename(filename: str) -> str:
    """Return logical file type based on extension."""
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".csv":
        return "scada"
    if ext == ".pdf":
        return "wellfile"
    raise ValueError("Unsupported file type")


def generate_file_path(root: str, well_id: str, file_type: str, filename: str) -> str:
    """Return destination path for a new upload."""
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    dest_dir = os.path.join(root, well_id, file_type)
    os.makedirs(dest_dir, exist_ok=True)
    return os.path.join(dest_dir, f"{ts}_{uuid.uuid4()}_{filename}")
