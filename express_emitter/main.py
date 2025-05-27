from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
from sentence_transformers import SentenceTransformer
import asyncio
import re
from shared.logger import logger

app = FastAPI(title="Genio EXPRESS Semantic Encoding Service")

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

@app.post("/encode", response_model=EncodeResponse)
async def encode(req: EncodeRequest):
    if not req.text or not req.text.strip():
        logger.warning("[EXPRESS] Empty text received")
        raise HTTPException(status_code=400, detail="Input text is empty")

    cleaned = preprocess_text(req.text)
    logger.info(f"[EXPRESS] Encoding uuid={req.uuid}")
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
