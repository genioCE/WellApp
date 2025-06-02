from fastapi import FastAPI, HTTPException
from datetime import datetime
from loguru import logger
from database import Database
from schemas import EmbedRequest
import redis.asyncio as redis
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram, Counter
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

redis_pool = redis.ConnectionPool.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}/0", decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)

# Prometheus metrics
embed_latency = Histogram("embed_latency_seconds", "Time spent embedding and storing")
embed_errors = Counter("embed_errors_total", "Total errors in Embed Memory service")

shutdown_event = asyncio.Event()


@app.on_event("startup")
async def startup():
    await db.connect()
    asyncio.create_task(redis_listener())


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


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
