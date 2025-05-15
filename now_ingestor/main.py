 
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from shared.schemas import NowSignal
from shared.redis_utils import publish
from shared.logger import logger

app = FastAPI()

@app.post("/ingest")
def ingest_signal(signal: NowSignal):
    logger.info(f"[NOW] Received: {signal}")
    publish("now_channel", signal.dict())
    return {"status": "published"}
