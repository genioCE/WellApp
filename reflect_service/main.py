from fastapi import FastAPI, HTTPException
from shared.logger import logger
from routes import router
from validation import validate_embedding
from schemas import AnchorResponse
from shared.redis_utils import subscribe, publish
import threading
import json
import asyncio
from datetime import datetime

app = FastAPI(title="Genio REFLECT Service")
app.include_router(router)

async def handle_message(data):
    uuid = data.get("uuid", datetime.utcnow().isoformat())
    pruned_embedding = data.get("pruned_embedding")

    if not pruned_embedding:
        logger.error(f"[REFLECT] Missing pruned_embedding for uuid={uuid}")
        return

    anchored, status, summary = await validate_embedding(pruned_embedding)
    logger.info(f"[REFLECT] uuid={uuid}, status={status}, summary={summary}")

    response = AnchorResponse(
        uuid=uuid,
        anchored_embedding=anchored,
        status=status,
        timestamp=datetime.utcnow(),
        summary=summary
    )

    publish("reflect_channel", response.dict())
    logger.info(f"[REFLECT] Published anchored embedding uuid={uuid} to 'reflect_channel'")

def listener():
    pubsub = subscribe("interpret_channel")
    logger.info("[REFLECT] Subscribed to 'interpret_channel'")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"])
                asyncio.run(handle_message(data))
            except Exception as e:
                logger.error(f"[REFLECT] Error processing message: {e}")

threading.Thread(target=listener, daemon=True).start()

@app.get("/")
async def healthcheck():
    return {"status": "reflect_service active"}
