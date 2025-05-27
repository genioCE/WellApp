from fastapi import FastAPI, HTTPException
from datetime import datetime
from .database import Database
from .schemas import EmbedRequest, EmbedResponse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("genio.embed")

app = FastAPI(title="Genio Embed Memory Service")

db = Database()

@app.on_event("startup")
async def startup() -> None:
    await db.connect()

@app.get("/")
async def healthcheck() -> dict:
    return {"status": "embed_memory_service active"}

@app.post("/embed", response_model=EmbedResponse)
async def embed_memory(req: EmbedRequest) -> EmbedResponse:
    timestamp = datetime.utcnow()
    metadata = req.metadata or {}
    try:
        metadata_id = await db.store_embedding(req.uuid, req.anchored_embedding, metadata, timestamp)
    except Exception as e:
        logger.exception("Failed to store embedding")
        raise HTTPException(status_code=500, detail="storage_failure") from e
    return EmbedResponse(uuid=req.uuid, stored=True, timestamp=timestamp, metadata_id=metadata_id)
