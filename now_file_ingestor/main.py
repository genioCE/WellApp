from __future__ import annotations

import os
import uuid
from typing import List

import asyncpg
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from .utils import parse_scada_csv, validate_hourly_sequence

app = FastAPI(title="Genio NOW File Ingestor")
Instrumentator().instrument(app).expose(app)

PGHOST = os.getenv("PGHOST", "postgres")
PGPORT = int(os.getenv("PGPORT", "5432"))
PGUSER = os.getenv("PGUSER", "user")
PGPASSWORD = os.getenv("PGPASSWORD", "password")
PGDATABASE = os.getenv("PGDATABASE", "database")
JZ_WELL_ID = os.getenv("JZ_WELL_ID", "11111111-1111-1111-1111-111111111111")

pool: asyncpg.Pool | None = None


@app.on_event("startup")
async def startup() -> None:
    global pool
    pool = await asyncpg.create_pool(
        host=PGHOST,
        port=PGPORT,
        user=PGUSER,
        password=PGPASSWORD,
        database=PGDATABASE,
    )
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scada_records (
                id SERIAL PRIMARY KEY,
                well_id UUID NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                flow_rate DOUBLE PRECISION,
                pressure DOUBLE PRECISION,
                temperature DOUBLE PRECISION,
                volume DOUBLE PRECISION
            )
            """
        )
    logger.info("[NOW_FILE] Database initialized")


@app.on_event("shutdown")
async def shutdown() -> None:
    if pool:
        await pool.close()


@app.post("/ingest/scada")
async def ingest_scada_csv(file: UploadFile = File(...)) -> dict[str, int]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")

    contents = await file.read()
    try:
        df = parse_scada_csv(contents)
    except Exception as exc:  # pragma: no cover - parse errors
        logger.error(f"[NOW_FILE] Parse error: {exc}")
        raise HTTPException(status_code=400, detail="Invalid CSV") from exc

    if len(df) != 8772:
        raise HTTPException(status_code=400, detail="Invalid row count")

    validate_hourly_sequence(df["timestamp"])

    records: List[tuple] = [
        (
            uuid.UUID(JZ_WELL_ID),
            pd.to_datetime(row.timestamp).to_pydatetime(),
            float(row.flow_rate),
            float(row.pressure),
            float(row.temperature),
            float(row.volume),
        )
        for row in df.itertuples(index=False)
    ]

    assert pool is not None
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO scada_records (
                well_id, timestamp, flow_rate, pressure, temperature, volume
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            records,
        )

    return {"rows_inserted": len(records)}


if __name__ == "__main__":  # pragma: no cover - manual start
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
