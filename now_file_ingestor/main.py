from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

import redis
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from .utils import classify_filename, generate_file_path

app = FastAPI(title="Genio NOW File Ingestor")
Instrumentator().instrument(app).expose(app)

REDIS_HOST = os.getenv("REDIS_HOST", "genio_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
RAW_DATA_ROOT = os.getenv("RAW_DATA_ROOT", "/mnt/data/raw")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50)) * 1024 * 1024
REDIS_CHANNEL = os.getenv("FILE_CHANNEL", "file_ingest")
EXPRESS_EMITTER_URL = os.getenv("EXPRESS_EMITTER_URL")

redis_client: Optional[redis.Redis] = None


@app.on_event("startup")
def startup() -> None:
    global redis_client
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    logger.info("[NOW_FILE] Redis connected", host=REDIS_HOST, port=REDIS_PORT)


@app.post("/ingest")
async def ingest_file(well_id: str = Form(...), file: UploadFile = File(...)) -> dict:
    """Store uploaded file and publish an ingestion event."""
    file_type = classify_filename(file.filename)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    path = generate_file_path(RAW_DATA_ROOT, well_id, file_type, file.filename)
    with open(path, "wb") as f:
        f.write(contents)

    payload = {
        "well_id": well_id,
        "file_type": file_type,
        "file_path": path,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if redis_client:
        redis_client.publish(REDIS_CHANNEL, json.dumps(payload))
        logger.info("[NOW_FILE] Published", channel=REDIS_CHANNEL, **payload)

    if EXPRESS_EMITTER_URL:
        try:
            requests.post(EXPRESS_EMITTER_URL, json=payload, timeout=5)
            logger.info("[NOW_FILE] Forwarded to express_emitter", url=EXPRESS_EMITTER_URL)
        except Exception as exc:  # pragma: no cover - network errors
            logger.error(f"[NOW_FILE] express_emitter failed: {exc}")

    return {"status": "stored", **payload}


if __name__ == "__main__":  # pragma: no cover - manual start
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
