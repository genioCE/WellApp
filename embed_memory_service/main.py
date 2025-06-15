from fastapi import FastAPI, HTTPException
from datetime import datetime
from loguru import logger
from database import Database
from schemas import EmbedRequest
import redis.asyncio as redis
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram, Counter
from qdrant_client.http import models as qm
import psycopg2
import uuid
import asyncio
import json
import os
import uvicorn

app = FastAPI(title="Genio Embed Memory Service")

# Instrument middleware immediately after FastAPI app creation
Instrumentator().instrument(app).expose(app)

db = Database()

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
VISUALIZE_CHANNEL = os.getenv("VISUALIZE_CHANNEL", "visualize_channel")
EMBED_CHANNEL = os.getenv("EMBED_CHANNEL", "embed_channel")
REPLAY_CHANNEL = os.getenv("REPLAY_CHANNEL", "replay_channel")

redis_pool = redis.ConnectionPool.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}/0", decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)

# Prometheus metrics
embed_latency = Histogram("embed_latency_seconds", "Time spent embedding and storing")
embed_errors = Counter("embed_errors_total", "Total errors in Embed Memory service")

shutdown_event = asyncio.Event()


def pg_connect() -> psycopg2.extensions.connection:
    """Return a new PostgreSQL connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("PGHOST", "postgres"),
        port=os.getenv("PGPORT", 5432),
        user=os.getenv("PGUSER", "user"),
        password=os.getenv("PGPASSWORD", "password"),
        dbname=os.getenv("PGDATABASE", "database"),
    )


def prepare_entries(points: list[qm.PointStruct]) -> list[tuple]:
    """Convert Qdrant points to tuples for DB insertion."""
    entries: list[tuple] = []
    for point in points:
        meta = point.payload or {}
        entries.append(
            (
                str(uuid.uuid4()),
                meta.get("well_id"),
                meta.get("source"),
                meta.get("timestamp") or meta.get("page"),
                meta.get("text"),
                meta.get("noun_phrases", []),
                meta.get("anomaly") or meta.get("important", False),
                str(point.id),
                meta.get("loop_stage"),
                meta.get("source_file"),
            )
        )
    return entries


def store_to_memory_log(points: list[qm.PointStruct]) -> None:
    """Persist points into the memory_log table."""
    if not points:
        return
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO memory_log (
                    memory_id, well_id, source, timestamp_or_page,
                    text, noun_phrases, anomaly_or_importance,
                    vector_id, loop_stage, source_file
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                prepare_entries(points),
            )
        conn.commit()
    finally:
        conn.close()


def mark_embedded(ids: list[str]) -> None:
    """Update Qdrant payload loop_stage to 'embedded'."""
    if not ids or not db.qdrant:
        return
    db.qdrant.set_payload(
        collection_name="genio_memory",
        payload={"loop_stage": "embedded"},
        points=ids,
    )


async def fetch_truth_points(well_id: str) -> list[qm.PointStruct]:
    """Retrieve all truth-stage points for a well from Qdrant."""
    if not db.qdrant:
        return []
    filt = qm.Filter(
        must=[
            qm.FieldCondition(key="well_id", match=qm.MatchValue(value=well_id)),
            qm.FieldCondition(key="loop_stage", match=qm.MatchValue(value="truth")),
        ]
    )
    points: list[qm.PointStruct] = []
    offset = None
    while True:
        batch, offset = await asyncio.to_thread(
            db.qdrant.scroll,
            collection_name="genio_memory",
            scroll_filter=filt,
            limit=100,
            offset=offset,
        )
        points.extend(batch)
        if offset is None:
            break
    return points


async def handle_embed_ready(well_id: str, source: str) -> None:
    """Process an embed_ready event for a given well."""
    points = await fetch_truth_points(well_id)
    store_to_memory_log(points)
    mark_embedded([str(p.id) for p in points])
    await redis_client.publish(
        REPLAY_CHANNEL,
        json.dumps({"event": "replay_ready", "well_id": well_id, "source": source}),
    )
    logger.info("[EMBED] Finalized %d embeddings for well %s", len(points), well_id)


@app.on_event("startup")
async def startup():
    await db.connect()
    asyncio.create_task(redis_listener())
    asyncio.create_task(embed_ready_listener())


@app.on_event("shutdown")
async def shutdown():
    shutdown_event.set()
    await redis_client.close()


@app.get("/health")
async def detailed_healthcheck():
    redis_status = "ok"
    db_status = "ok"

    try:
        await redis_client.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"
        logger.error(f"[EMBED] Redis health check failed: {e}")

    try:
        async with db.pg_pool.acquire() as conn:
            await conn.execute("SELECT 1")
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"[EMBED] Database health check failed: {e}")

    return {
        "status": "active",
        "redis": redis_status,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def healthcheck():
    return {"status": "embed_memory_service active"}


async def redis_listener():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(VISUALIZE_CHANNEL)
    logger.info(f"[EMBED] Subscribed to '{VISUALIZE_CHANNEL}'")

    while not shutdown_event.is_set():
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if message:
            try:
                data = json.loads(message["data"])
                asyncio.create_task(handle_embedding(data))
            except Exception as e:
                embed_errors.inc()
                logger.error("[EMBED] Error processing message", error=str(e))


async def handle_embedding(data):
    uuid = data.get("uuid", datetime.utcnow().isoformat())
    anchored_embedding = data.get("anchored_embedding")
    metadata = data.get("metadata", {})
    timestamp = datetime.utcnow()

    if not anchored_embedding:
        embed_errors.inc()
        logger.error("[EMBED] Missing anchored_embedding", uuid=uuid)
        return

    try:
        with embed_latency.time():
            metadata_id = await db.store_embedding(
                uuid, anchored_embedding, metadata, timestamp
            )
        await redis_client.publish(
            EMBED_CHANNEL, json.dumps({"uuid": uuid, "metadata_id": metadata_id})
        )
        logger.info("[EMBED] Stored and published", uuid=uuid, metadata_id=metadata_id)
    except Exception as e:
        embed_errors.inc()
        logger.error("[EMBED] Error storing embedding", uuid=uuid, error=str(e))


async def embed_ready_listener():
    """Listen for embed_ready events and finalize memory capture."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(EMBED_CHANNEL)
    logger.info(f"[EMBED] Subscribed to '{EMBED_CHANNEL}'")
    while not shutdown_event.is_set():
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if not message:
            continue
        try:
            data = json.loads(message["data"])
            if data.get("event") != "embed_ready":
                continue
            well_id = data["well_id"]
            source = data.get("source", "unknown")
            await handle_embed_ready(well_id, source)
        except Exception as exc:
            logger.error(f"[EMBED] Failed to process embed_ready: {exc}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
