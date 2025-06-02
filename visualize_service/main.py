from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from loguru import logger
from schemas import VisualizeRequest, VisualizeResponse
from visualization import generate_visualization
import redis.asyncio as redis
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram, Counter
import asyncio
import json
import os
import uvicorn

app = FastAPI(title="Genio Visualize Service")
app.mount("/static", StaticFiles(directory="."), name="static")

# Immediately after app creation (correct middleware placement)
Instrumentator().instrument(app).expose(app)

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REFLECT_CHANNEL = os.getenv("REFLECT_CHANNEL", "reflect_channel")
VISUALIZE_CHANNEL = os.getenv("VISUALIZE_CHANNEL", "visualize_channel")

redis_pool = redis.ConnectionPool.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}/0", decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)

# Prometheus metrics
visualization_latency = Histogram(
    "visualization_latency_seconds", "Time spent generating visualizations"
)
visualize_errors = Counter(
    "visualize_errors_total", "Total errors in Visualize service"
)

shutdown_event = asyncio.Event()


async def process_message(data):
    req = VisualizeRequest(
        uuid=data["uuid"],
        anchored_embedding=data["anchored_embedding"],
        method=data.get("method", "pca"),
        dimensions=data.get("dimensions", 2),
    )
    try:
        with visualization_latency.time():
            path, vis_type = await generate_visualization(
                req.anchored_embedding, req.method, req.dimensions
            )
        url = f"/static/{path}"
        response = {
            "uuid": req.uuid,
            "visualization_url": url,
            "visualization_type": vis_type,
            "timestamp": datetime.utcnow().isoformat(),
            "anchored_embedding": req.anchored_embedding,
        }
        await redis_client.publish(VISUALIZE_CHANNEL, json.dumps(response))
        logger.info("[VISUALIZE] Published visualization", uuid=req.uuid)
    except Exception as e:
        visualize_errors.inc()
        logger.error("[VISUALIZE] Error generating visualization", error=str(e))


async def listener():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(REFLECT_CHANNEL)
    logger.info(f"[VISUALIZE] Subscribed to '{REFLECT_CHANNEL}'")

    while not shutdown_event.is_set():
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if message:
            try:
                data = json.loads(message["data"])
                asyncio.create_task(process_message(data))
            except Exception as e:
                visualize_errors.inc()
                logger.error("[VISUALIZE] Failed to process message", error=str(e))


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listener())


@app.on_event("shutdown")
async def shutdown_event_trigger():
    shutdown_event.set()
    await redis_client.close()


@app.post("/visualize", response_model=VisualizeResponse)
async def visualize(req: VisualizeRequest):
    logger.info("[VISUALIZE] HTTP Request", uuid=req.uuid)
    try:
        with visualization_latency.time():
            path, vis_type = await generate_visualization(
                req.anchored_embedding, req.method, req.dimensions
            )
        url = f"/static/{path}"
        return VisualizeResponse(
            uuid=req.uuid,
            visualization_url=url,
            visualization_type=vis_type,
            timestamp=datetime.utcnow(),
        )
    except ValueError as e:
        visualize_errors.inc()
        logger.error("[VISUALIZE] Invalid request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        visualize_errors.inc()
        logger.error("[VISUALIZE] Error generating visualization", error=str(e))
        raise HTTPException(status_code=500, detail="Visualization failed")


@app.get("/health")
async def detailed_healthcheck():
    redis_status = "ok"
    try:
        await redis_client.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "status": "active",
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def healthcheck():
    return {"status": "visualize_service active"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
