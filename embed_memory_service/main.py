from fastapi import FastAPI
from datetime import datetime
from database import Database
from schemas import EmbedRequest
from shared.logger import logger
from shared.redis_utils import subscribe, publish
import asyncio
import json

app = FastAPI(title="Genio Embed Memory Service")
db = Database()

@app.on_event("startup")
async def startup():
    await db.connect()
    asyncio.create_task(redis_listener())  # Explicitly launches listener correctly

@app.get("/")
async def healthcheck():
    return {"status": "embed_memory_service active"}

async def redis_listener():
    pubsub = subscribe("visualize_channel")
    logger.info("[EMBED] Subscribed to 'visualize_channel'")

    loop = asyncio.get_running_loop()

    while True:
        message = await loop.run_in_executor(None, pubsub.get_message, True, None)
        if message and message["type"] == "message":
            try:
                data = json.loads(message["data"])
                await handle_embedding(data)
            except Exception as e:
                logger.error(f"[EMBED] Error processing message: {e}")

async def handle_embedding(data):
    uuid = data.get("uuid", datetime.utcnow().isoformat())
    anchored_embedding = data.get("anchored_embedding")
    metadata = data.get("metadata", {})
    timestamp = datetime.utcnow()

    if not anchored_embedding:
        logger.error(f"[EMBED] Missing anchored_embedding for uuid={uuid}")
        return

    try:
        metadata_id = await db.store_embedding(uuid, anchored_embedding, metadata, timestamp)
        publish("embed_channel", {"uuid": uuid, "metadata_id": metadata_id})
        logger.info(f"[EMBED] Stored and published uuid={uuid}")
    except Exception as e:
        logger.error(f"[EMBED] Error storing embedding uuid={uuid}: {e}")
