from fastapi import FastAPI, HTTPException
from shared.logger import logger
from routes import router
from validation import validate_embedding
from schemas import AnchorResponse
import redis.asyncio as redis
from loguru import logger
from processor import listen_for_signals, stop_listener
import threading
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram, Counter
import asyncio
import json
import os
from datetime import datetime
import signal
import uvicorn

app = FastAPI(title="Genio REFLECT Service")

# Instrument Prometheus metrics immediately after app creation
Instrumentator().instrument(app).expose(app)

app.include_router(router)

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
INTERPRET_CHANNEL = os.getenv("INTERPRET_CHANNEL", "interpret_channel")
REFLECT_CHANNEL = os.getenv("REFLECT_CHANNEL", "reflect_channel")

redis_pool = redis.ConnectionPool.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}/0", decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)

# Prometheus metrics
validation_latency = Histogram(
    "validation_latency_seconds", "Embedding validation latency"
)
reflect_errors = Counter("reflect_errors_total", "Total errors in Reflect service")

shutdown_event = asyncio.Event()


async def handle_message(data):
    uuid = data.get("uuid", datetime.utcnow().isoformat())
    pruned_embedding = data.get("pruned_embedding")

    if not pruned_embedding:
        reflect_errors.inc()
        logger.error("[REFLECT] Missing pruned_embedding", uuid=uuid)
        return

    try:
        with validation_latency.time():
            anchored, status, summary = await validate_embedding(pruned_embedding)
    except Exception as e:
        reflect_errors.inc()
        logger.error("[REFLECT] Validation error", uuid=uuid, error=str(e))
        return

    response = AnchorResponse(
        uuid=uuid,
        anchored_embedding=anchored,
        status=status,
        timestamp=datetime.utcnow(),
        summary=summary,
    )

    # Corrected serialization using response.json()
    await redis_client.publish(REFLECT_CHANNEL, response.json())
    logger.info("[REFLECT] Published anchored embedding", uuid=uuid, status=status)


async def listener():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(INTERPRET_CHANNEL)
    logger.info(f"[REFLECT] Subscribed to '{INTERPRET_CHANNEL}'")

    while not shutdown_event.is_set():
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if message:
            try:
                data = json.loads(message["data"])
                asyncio.create_task(handle_message(data))
            except Exception as e:
                reflect_errors.inc()
                logger.error("[REFLECT] Error processing message", error=str(e))


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listener())
    threading.Thread(target=listen_for_signals, daemon=True).start()


@app.on_event("shutdown")
async def shutdown_event_trigger():
    shutdown_event.set()
    stop_listener()
    await redis_client.close()


@app.get("/health")
async def detailed_healthcheck():
    redis_status = "ok"
    validation_status = "ok"
    try:
        await redis_client.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"

    try:
        await validate_embedding([0.0])  # minimal test embedding
    except Exception as e:
        validation_status = f"error: {str(e)}"

    return {
        "status": "active",
        "redis": redis_status,
        "validation_module": validation_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def healthcheck():
    return {"status": "reflect_service active"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
