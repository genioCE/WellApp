import os
import re
import json
import asyncio
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram
from loguru import logger
import redis.asyncio as redis

from shared.config import REDIS_HOST, REDIS_PORT

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
    'embedding_generation_seconds',
    'Time spent generating embeddings'
)

# Environment configurations
MODEL_NAME = os.getenv("MODEL_NAME", "all-MiniLM-L6-v2")
NOW_CHANNEL = os.getenv("NOW_CHANNEL", "now_channel")
EXPRESS_CHANNEL = os.getenv("EXPRESS_CHANNEL", "express_channel")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))

model = SentenceTransformer(MODEL_NAME)

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
                data = json.loads(message['data'])
                uuid = data.get('uuid', datetime.utcnow().isoformat())
                content = data['content']
                buffer.append((uuid, content))
            except Exception as e:
                logger.error(f"[EXPRESS] Message handling error: {e}")

        # Check if buffer should be flushed by size or time
        if buffer and (len(buffer) >= BATCH_SIZE or (now - buffer_timer).total_seconds() >= flush_interval):
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
            "content": content
        }
        await redis_client.publish(EXPRESS_CHANNEL, json.dumps(payload))
        logger.info("[EXPRESS] Published embedding", uuid=uuid)

# Startup event: only tasks needing asynchronous context here
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(handle_now_channel())

# HTTP API endpoint for single embedding generation
@app.post("/encode", response_model=EncodeResponse)
async def encode(req: EncodeRequest):
    if not req.text.strip():
        logger.warning("[EXPRESS] Empty text received", uuid=req.uuid)
        raise HTTPException(status_code=400, detail="Input text is empty")

    cleaned = preprocess_text(req.text)
    with embedding_latency.time():
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, model.encode, cleaned)

    logger.info("[EXPRESS] Encoded via API", uuid=req.uuid)

    return EncodeResponse(
        uuid=req.uuid,
        embedding=embedding.tolist(),
        timestamp=datetime.utcnow(),
        model=MODEL_NAME
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
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
