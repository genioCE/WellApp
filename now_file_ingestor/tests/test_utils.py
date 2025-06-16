import os
import sys
import types
import importlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

import pytest

from now_file_ingestor.utils import (
    parse_scada_csv,
    validate_hourly_sequence,
    classify_filename,
    generate_file_path,
)


def get_pandas():
    if "pandas" in sys.modules:
        del sys.modules["pandas"]
    return importlib.import_module("pandas")


def test_parse_scada_csv_missing_columns():
    data = b"timestamp,flow_rate\n2024-01-01T00:00Z,1.0"
    with pytest.raises(ValueError):
        parse_scada_csv(data)


def test_validate_hourly_sequence_success():
    pd = get_pandas()
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=3, freq="H")})
    validate_hourly_sequence(df["timestamp"])


def test_validate_hourly_sequence_failure():
    pd = get_pandas()
    df = pd.DataFrame({"timestamp": ["2024-01-01 00:00", "2024-01-01 02:00"]})
    with pytest.raises(ValueError):
        validate_hourly_sequence(df["timestamp"])


def test_classify_filename():
    assert classify_filename("test.csv") == "scada"
    assert classify_filename("something.PDF") == "wellfile"
    with pytest.raises(ValueError):
        classify_filename("other.txt")


def test_generate_file_path(tmp_path):
    path = generate_file_path(str(tmp_path), "well1", "scada", "x.csv")
    assert path.startswith(os.path.join(str(tmp_path), "well1", "scada"))
