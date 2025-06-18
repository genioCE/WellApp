import os
import re
import json
import asyncio
from datetime import datetime
from typing import List, Any, Dict

from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel
import pandas as pd
import fitz
import psycopg2
from psycopg2.extras import execute_batch
from sentence_transformers import SentenceTransformer
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram
from loguru import logger
import redis.asyncio as redis

from shared.config import (
    REDIS_HOST,
    REDIS_PORT,
    PGHOST,
    PGPORT,
    PGUSER,
    PGPASSWORD,
    PGDATABASE,
)


from shared.scada_utils import parse_scada_timestamp


# FastAPI app initialization
app = FastAPI(title="Genio EXPRESS Semantic Encoding Service")

# Middleware instrumentation immediately after app creation
Instrumentator().instrument(app).expose(app)

# Redis connection setup
redis_pool = redis.ConnectionPool.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}/0", decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)

# Prometheus metrics
embedding_latency = Histogram(
    "embedding_generation_seconds", "Time spent generating embeddings"
)

# Environment configurations
MODEL_NAME = os.getenv("MODEL_NAME", "all-MiniLM-L6-v2")
NOW_CHANNEL = os.getenv("NOW_CHANNEL", "now_channel")
EXPRESS_CHANNEL = os.getenv("EXPRESS_CHANNEL", "express_channel")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
INGEST_CHANNEL = os.getenv("INGEST_CHANNEL", "ingest_channel")
INTERPRET_CHANNEL = os.getenv("INTERPRET_CHANNEL", "interpret_channel")
INTERPRET_SERVICE_URL = os.getenv(
    "INTERPRET_SERVICE_URL",
    "http://interpret_service:8000/snapshot",
)

model: SentenceTransformer | None = None


# Request and Response Schemas
class EncodeRequest(BaseModel):
    uuid: str
    text: str


class EncodeResponse(BaseModel):
    uuid: str
    embedding: List[float]
    timestamp: datetime
    model: str


# Text preprocessing utility
def preprocess_text(text: str) -> str:
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


# Batch embedding function
async def encode_batch(texts: List[str]) -> List[List[float]]:
    assert model is not None
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(None, model.encode, texts)
    return [emb.tolist() for emb in embeddings]


# Redis listener for batching embeddings
async def handle_now_channel():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(NOW_CHANNEL)
    buffer = []
    buffer_timer = datetime.utcnow()
    flush_interval = 1  # seconds
    logger.info(f"[EXPRESS] Subscribed to Redis channel '{NOW_CHANNEL}'")

    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
        now = datetime.utcnow()

        if message:
            try:
                data = json.loads(message["data"])
                uuid = data.get("uuid", datetime.utcnow().isoformat())
                content = data["content"]
                buffer.append((uuid, content))
            except Exception as e:
                logger.error(f"[EXPRESS] Message handling error: {e}")

        # Check if buffer should be flushed by size or time
        if buffer and (
            len(buffer) >= BATCH_SIZE
            or (now - buffer_timer).total_seconds() >= flush_interval
        ):
            await process_batch(buffer)
            buffer.clear()
            buffer_timer = now


async def process_batch(batch):
    uuids, contents = zip(*batch)
    cleaned_texts = [preprocess_text(text) for text in contents]

    with embedding_latency.time():
        embeddings = await encode_batch(cleaned_texts)

    timestamp = datetime.utcnow().isoformat()
    for uuid, embedding, content in zip(uuids, embeddings, contents):
        payload = {
            "uuid": uuid,
            "embedding": embedding,
            "timestamp": timestamp,
            "content": content,
        }
        await redis_client.publish(EXPRESS_CHANNEL, json.dumps(payload))
        logger.info("[EXPRESS] Published embedding", uuid=uuid)


# -----------------------------------------------------------
# Snapshot emission utilities
# -----------------------------------------------------------

async def post_snapshot(snapshot: Dict[str, Any]) -> None:
    """Send a snapshot to the interpret service via HTTP."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(INTERPRET_SERVICE_URL, json=snapshot, timeout=5)
    except Exception as exc:
        logger.error(f"[EXPRESS] Failed to POST snapshot: {exc}")


# -----------------------------------------------------------
# Ingest worker utilities
# -----------------------------------------------------------
def parse_scada_csv(path: str, well_id: str) -> List[Dict[str, Any]]:
    """Yield SCADA CSV rows as dictionaries."""

    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "DateTime": "timestamp",
            "flow_rate_mcf_day": "flow_rate",
            "static_pressure_psia": "pressure",
            "temperature_degF": "temperature",
            "volume_mcf": "volume",
        }
    )
    if "timestamp" in df:
        df["timestamp"] = df["timestamp"].apply(parse_scada_timestamp)

    df["well_id"] = well_id
    df["source_file"] = path

    cols = [
        "well_id",
        "timestamp",
        "flow_rate",
        "pressure",
        "temperature",
        "volume",
        "source_file",
    ]

    rows = []
    for row in df[cols].itertuples(index=False):
        rows.append({
            "well_id": row.well_id,
            "timestamp": row.timestamp,
            "flow_rate": row.flow_rate,
            "pressure": row.pressure,
            "temperature": row.temperature,
            "volume": row.volume,
            "source_file": row.source_file,
        })
    return rows


def parse_wellfile_pdf(path: str, well_id: str) -> List[Dict[str, Any]]:
    """Return the first sentence from each PDF page."""

    try:
        import spacy
    except Exception:  # pragma: no cover - optional dependency
        spacy = None
    try:
        from paddleocr import PaddleOCR
    except Exception:  # pragma: no cover - optional dependency
        PaddleOCR = None

    nlp = spacy.load("en_core_web_sm") if spacy else None
    ocr = PaddleOCR(use_angle_cls=True, lang="en") if PaddleOCR else None

    doc = fitz.open(path)
    rows: List[Dict[str, Any]] = []
    for page_idx, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if not text and ocr:
            try:
                pix = page.get_pixmap()
                result = ocr.ocr(pix.tobytes("png"), cls=True)
                text = " ".join(r[1][0] for r in result[0]) if result else ""
            except Exception:
                text = ""

        sentence = ""
        if nlp:
            doc_s = nlp(text)
            for sent in doc_s.sents:
                if sent.text.strip():
                    sentence = sent.text.strip()
                    break
        else:
            if "." in text:
                sentence = text.split(".", 1)[0].strip() + "."
            else:
                sentence = text.strip()

        if sentence:
            rows.append(
                {
                    "well_id": well_id,
                    "page": page_idx,
                    "text": sentence,
                    "source_file": path,
                }
            )
    doc.close()
    return rows


def scada_rows_to_snapshots(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create snapshots from SCADA rows."""

    snapshots = []
    for row in rows:
        sentence = (
            f"At {row['timestamp']}, flow {row['flow_rate']} mcf/day "
            f"and pressure {row['pressure']} psi."
        )
        snapshots.append(
            {
                "sentence": sentence,
                "timestamp": row["timestamp"],
                "source": "scada",
                "well_id": row["well_id"],
            }
        )
    return snapshots


def wellfile_rows_to_snapshots(rows: List[Dict[str, Any]], well_id: str) -> List[Dict[str, Any]]:
    """Create snapshots from wellfile rows."""

    ts = datetime.utcnow().isoformat()
    return [
        {
            "sentence": r["text"],
            "timestamp": ts,
            "source": "wellfile",
            "well_id": well_id,
        }
        for r in rows
    ]


def init_db() -> None:
    """Ensure snapshot tables exist."""

    conn = psycopg2.connect(
        host=PGHOST, port=PGPORT, user=PGUSER, password=PGPASSWORD, dbname=PGDATABASE
    )
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshot_scada (
                    id SERIAL PRIMARY KEY,
                    well_id UUID NOT NULL,
                    timestamp TIMESTAMP,
                    flow_rate REAL,
                    pressure REAL,
                    temperature REAL,
                    volume REAL,
                    source_file TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshot_wellfile (
                    id SERIAL PRIMARY KEY,
                    well_id UUID NOT NULL,
                    page INT,
                    text TEXT,
                    source_file TEXT
                )
                """
            )
    conn.close()


def store_scada_rows(rows: list[Dict[str, Any]]) -> None:
    """Persist SCADA rows to the database."""

    conn = psycopg2.connect(
        host=PGHOST, port=PGPORT, user=PGUSER, password=PGPASSWORD, dbname=PGDATABASE
    )
    with conn:
        with conn.cursor() as cur:
            execute_batch(
                cur,
                """
                INSERT INTO snapshot_scada (
                    well_id, timestamp, flow_rate, pressure, temperature, volume, source_file
                ) VALUES (
                    %(well_id)s, %(timestamp)s, %(flow_rate)s, %(pressure)s, %(temperature)s, %(volume)s, %(source_file)s
                )
                """,
                rows,
            )
    conn.close()


def store_wellfile_rows(rows: list[Dict[str, Any]]) -> None:
    """Persist well file rows to the database."""

    conn = psycopg2.connect(
        host=PGHOST, port=PGPORT, user=PGUSER, password=PGPASSWORD, dbname=PGDATABASE
    )
    with conn:
        with conn.cursor() as cur:
            execute_batch(
                cur,
                """
                INSERT INTO snapshot_wellfile (
                    well_id, page, text, source_file
                ) VALUES (
                    %(well_id)s, %(page)s, %(text)s, %(source_file)s
                )
                """,
                rows,
            )
    conn.close()


async def process_scada_event(payload: Dict[str, Any]) -> None:
    """Handle scada_ingest_ready event."""

    rows = await asyncio.to_thread(
        parse_scada_csv, payload["file_path"], payload["well_id"]
    )
    await asyncio.to_thread(store_scada_rows, rows)

    snapshots = scada_rows_to_snapshots(rows)
    count = 0
    for snap in snapshots:
        await post_snapshot(snap)
        count += 1

    await redis_client.publish(
        INTERPRET_CHANNEL,
        json.dumps(
            {
                "event": "interpret_ready",
                "well_id": payload["well_id"],
                "source": "scada",
            }
        ),
    )
    logger.info(
        "[EXPRESS] Stored SCADA snapshot", well_id=payload["well_id"], count=count
    )


async def process_wellfile_event(payload: Dict[str, Any]) -> None:
    """Handle wellfile_ingest_ready event."""

    rows = await asyncio.to_thread(
        parse_wellfile_pdf, payload["file_path"], payload["well_id"]
    )
    await asyncio.to_thread(store_wellfile_rows, rows)

    snapshots = wellfile_rows_to_snapshots(rows, payload["well_id"])
    count = 0
    for snap in snapshots:
        await post_snapshot(snap)
        count += 1

    await redis_client.publish(
        INTERPRET_CHANNEL,
        json.dumps(
            {
                "event": "interpret_ready",
                "well_id": payload["well_id"],
                "source": "wellfile",
            }
        ),
    )
    logger.info(
        "[EXPRESS] Stored WELLFILE snapshot", well_id=payload["well_id"], count=count
    )


async def handle_ingest_channel() -> None:
    """Background worker listening for ingest events."""

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(INGEST_CHANNEL)
    logger.info(f"[EXPRESS] Subscribed to Redis channel '{INGEST_CHANNEL}'")

    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
        if not message:
            await asyncio.sleep(0.1)
            continue

        try:
            payload = json.loads(message["data"])
            event = payload.get("event")
            if event == "scada_ingest_ready":
                await process_scada_event(payload)
            elif event == "wellfile_ingest_ready":
                await process_wellfile_event(payload)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(f"[EXPRESS] Error handling ingest event: {exc}")


# Startup event: only tasks needing asynchronous context here
@app.on_event("startup")
async def startup_event():
    global model
    model = SentenceTransformer(MODEL_NAME)
    init_db()
    asyncio.create_task(handle_now_channel())
    asyncio.create_task(handle_ingest_channel())


# HTTP API endpoint for single embedding generation
@app.post("/encode", response_model=EncodeResponse)
async def encode(req: EncodeRequest):
    if not req.text.strip():
        logger.warning("[EXPRESS] Empty text received", uuid=req.uuid)
        raise HTTPException(status_code=400, detail="Input text is empty")

    assert model is not None
    cleaned = preprocess_text(req.text)
    with embedding_latency.time():
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, model.encode, cleaned)

    logger.info("[EXPRESS] Encoded via API", uuid=req.uuid)

    return EncodeResponse(
        uuid=req.uuid,
        embedding=embedding.tolist(),
        timestamp=datetime.utcnow(),
        model=MODEL_NAME,
    )


# Enhanced health check endpoint
@app.get("/health")
async def detailed_healthcheck():
    redis_status = "ok"
    model_status = "ok"

    try:
        await redis_client.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"

    try:
        _ = model.encode("test")
    except Exception as e:
        model_status = f"error: {str(e)}"

    return {
        "status": "active",
        "redis": redis_status,
        "model": model_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
