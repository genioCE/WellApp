import os
import tempfile
import pandas as pd
import fitz
from express_emitter.main import (
    parse_scada_csv,
    parse_wellfile_pdf,
    scada_rows_to_snapshots,
    wellfile_rows_to_snapshots,
)
from now_ingestor.scada_utils import parse_scada_timestamp


def test_parse_scada_csv():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "scada.csv")
        df = pd.DataFrame({
            "DateTime": ["05/07/2024 00:00-01:00"],
            "flow_rate_mcf_day": [5.0],
            "static_pressure_psia": [2.0],
            "temperature_degF": [3.0],
            "volume_mcf": [4.0],
        })
        df.to_csv(path, index=False)
        rows = list(parse_scada_csv(path, "11111111-1111-1111-1111-111111111111"))
        assert len(rows) == 1
        row = rows[0]
        assert row["flow_rate"] == 5.0
        assert row["pressure"] == 2.0
        assert row["temperature"] == 3.0
        assert row["volume"] == 4.0
        assert row["timestamp"] == parse_scada_timestamp("05/07/2024 00:00-01:00")

        snaps = scada_rows_to_snapshots(rows)
        assert len(snaps) == 1
        snap = snaps[0]
        assert snap["source"] == "scada"
        assert snap["well_id"] == "11111111-1111-1111-1111-111111111111"


def test_parse_wellfile_pdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "First paragraph long enough.\n\nShort.\n\nSecond long paragraph here.")
    doc.save(pdf_path)
    doc.close()
    rows = parse_wellfile_pdf(str(pdf_path), "abcd")
    assert rows
    assert len(rows) == 1
    assert "First" in rows[0]["text"]

    snaps = wellfile_rows_to_snapshots(rows, "abcd")
    assert snaps[0]["source"] == "wellfile"
