import os
import tempfile
import pandas as pd
import fitz
import types
import sys

dummy_openai = types.ModuleType("openai")
dummy_openai.__spec__ = types.SimpleNamespace()
sys.modules["openai"] = dummy_openai

from express_emitter.main import parse_scada_csv, parse_wellfile_pdf
from now_ingestor.scada_utils import parse_scada_timestamp


def test_parse_scada_csv():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "scada.csv")
        df = pd.DataFrame(
            {
                "DateTime": ["05/07/2024 00:00-01:00"],
                "flow_rate_mcf_day": [5.0],
                "static_pressure_psia": [2.0],
                "temperature_degF": [3.0],
                "volume_mcf": [4.0],
            }
        )
        df.to_csv(path, index=False)
        rows = parse_scada_csv(path, "11111111-1111-1111-1111-111111111111")
        assert len(rows) == 1
        row = rows[0]
        assert row["flow_rate"] == 5.0
        assert row["pressure"] == 2.0
        assert row["temperature"] == 3.0
        assert row["volume"] == 4.0
        assert row["timestamp"] == parse_scada_timestamp("05/07/2024 00:00-01:00")


def test_parse_wellfile_pdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "First paragraph long enough.\n\nShort.\n\nSecond long paragraph here.",
    )
    doc.save(pdf_path)
    doc.close()
    rows = parse_wellfile_pdf(str(pdf_path), "abcd")
    assert rows
    assert all(len(r["text"]) >= 15 for r in rows)
