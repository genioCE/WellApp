from fastapi import FastAPI, HTTPException
from shared.redis_utils import subscribe, publish
from shared.logger import logger
import threading
import json
import spacy
import os
from datetime import datetime
from schemas import PruneRequest, PruneResponse
from pruning import prune_embedding

app = FastAPI(title="Genio INTERPRET Service")

# Load spaCy model safely
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    logger.error(f"Failed to load spaCy model: {e}")
    exit(1)

# Settings for semantic pruning
THRESHOLD = float(os.getenv("PRUNE_THRESHOLD", "0.1"))
REDUCE_DIM = int(os.getenv("REDUCE_DIM", "0"))

def listener():
    pubsub = subscribe("express_channel")
    logger.info("[INTERPRET] Subscribed to 'express_channel'")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"])
                content = data.get("content")
                embedding = data.get("embedding")
                uuid = data.get("uuid", datetime.utcnow().isoformat())

                if not embedding:
                    logger.error(f"[INTERPRET] Missing embedding for uuid={uuid}")
                    continue

                # Tokenize content
                doc = nlp(content)
                tokens = [token.text for token in doc if not token.is_stop]
                logger.info(f"[INTERPRET] Parsed Tokens: {tokens}")

                # Prune embedding
                pruned_embedding, details = prune_embedding(
                    embedding, THRESHOLD, REDUCE_DIM if REDUCE_DIM > 0 else None
                )
                logger.info(f"[INTERPRET] Pruned embedding uuid={uuid}, details={details}")

                # Build message for downstream service
                downstream_message = {
                    "uuid": uuid,
                    "tokens": tokens,
                    "pruned_embedding": pruned_embedding,
                    "pruning_details": details,
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Publish clearly to the next channel
                publish("interpret_channel", downstream_message)
                logger.info(f"[INTERPRET] Published processed data uuid={uuid} to 'interpret_channel'")

            except Exception as e:
                logger.error(f"[INTERPRET] Error processing message: {e}")

# Start listener thread
threading.Thread(target=listener, daemon=True).start()

@app.get("/")
def healthcheck():
    return {"status": "interpret_service active"}

@app.post("/prune", response_model=PruneResponse)
async def prune(req: PruneRequest):
    if not req.embedding:
        raise HTTPException(status_code=400, detail="Embedding vector missing")
    try:
        pruned, details = prune_embedding(
            req.embedding, THRESHOLD, REDUCE_DIM if REDUCE_DIM > 0 else None
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to prune embedding: {e}")

    return PruneResponse(
        uuid=req.uuid,
        pruned_embedding=pruned,
        timestamp=datetime.utcnow(),
        details=details,
    )

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
