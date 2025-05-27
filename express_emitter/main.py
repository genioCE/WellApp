from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
from sentence_transformers import SentenceTransformer
import asyncio
import re
import json
import redis.asyncio as redis
from shared.logger import logger
from shared.config import REDIS_HOST, REDIS_PORT

app = FastAPI(title="Genio EXPRESS Semantic Encoding Service")

# Initialize Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)

class EncodeRequest(BaseModel):
    uuid: str
    text: str

class EncodeResponse(BaseModel):
    uuid: str
    embedding: List[float]
    timestamp: datetime
    model: str

def preprocess_text(text: str) -> str:
    """Basic cleaning and whitespace normalization."""
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())

async def publish_embedding(response: EncodeResponse):
    channel = "express_channel"
    await redis_client.publish(channel, response.json())
    logger.info(f"[EXPRESS] Published embedding uuid={response.uuid} to channel={channel}")

async def handle_now_channel(pubsub):
    channel = "now_channel"
    await pubsub.subscribe(channel)
    logger.info(f"[EXPRESS] Subscribed to Redis channel '{channel}'")

    async for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                uuid = data.get('uuid', datetime.utcnow().isoformat())
                content = data['content']

                cleaned = preprocess_text(content)
                logger.info(f"[EXPRESS] Encoding uuid={uuid}")
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(None, model.encode, cleaned)

                response = {
                    "uuid": uuid,
                    "embedding": embedding.tolist(),
                    "timestamp": datetime.utcnow().isoformat(),
                    "content": content  # <-- ADD THIS LINE explicitly
                }

                await redis_client.publish("express_channel", json.dumps(response))
                logger.info(f"[EXPRESS] Published embedding and content uuid={uuid} to 'express_channel'")

            except Exception as e:
                logger.error(f"[EXPRESS] Failed to process message: {e}")

@app.on_event("startup")
async def startup_event():
    pubsub = redis_client.pubsub()
    asyncio.create_task(handle_now_channel(pubsub))

@app.post("/encode", response_model=EncodeResponse)
async def encode(req: EncodeRequest):
    if not req.text or not req.text.strip():
        logger.warning("[EXPRESS] Empty text received")
        raise HTTPException(status_code=400, detail="Input text is empty")

    cleaned = preprocess_text(req.text)
    logger.info(f"[EXPRESS] Encoding via API uuid={req.uuid}")
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, model.encode, cleaned)
    return EncodeResponse(
        uuid=req.uuid,
        embedding=embedding.tolist(),
        timestamp=datetime.utcnow(),
        model=MODEL_NAME,
    )

@app.get("/")
async def healthcheck():
    return {"status": "express_emitter active"}
