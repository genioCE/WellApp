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
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram, Counter
import signal
import uvicorn

app = FastAPI(title="Genio INTERPRET Service")

# Middleware and Prometheus instrumentation must be here
Instrumentator().instrument(app).expose(app)

# Prometheus metrics
pruning_latency = Histogram("pruning_latency_seconds", "Time spent pruning embeddings")
interpret_errors = Counter(
    "interpret_errors_total", "Total errors in Interpret service"
)

# Load spaCy model safely
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    logger.error(f"Failed to load spaCy model: {e}")
    exit(1)

# Settings
THRESHOLD = float(os.getenv("PRUNE_THRESHOLD", "0.1"))
REDUCE_DIM = int(os.getenv("REDUCE_DIM", "0"))
EXPRESS_CHANNEL = os.getenv("EXPRESS_CHANNEL", "express_channel")
INTERPRET_CHANNEL = os.getenv("INTERPRET_CHANNEL", "interpret_channel")

shutdown_flag = threading.Event()


def listener():
    pubsub = subscribe(EXPRESS_CHANNEL)
    logger.info(f"[INTERPRET] Subscribed to '{EXPRESS_CHANNEL}'")

    while not shutdown_flag.is_set():
        message = pubsub.get_message(timeout=1)
        if message and message["type"] == "message":
            try:
                data = json.loads(message["data"])
                content = data.get("content")
                embedding = data.get("embedding")
                uuid = data.get("uuid", datetime.utcnow().isoformat())

                if not embedding:
                    interpret_errors.inc()
                    logger.error(f"[INTERPRET] Missing embedding for uuid={uuid}")
                    continue

                doc = nlp(content)
                tokens = [token.text for token in doc if not token.is_stop]
                logger.info(f"[INTERPRET] Parsed Tokens: {tokens}")

                with pruning_latency.time():
                    pruned_embedding, details = prune_embedding(
                        embedding, THRESHOLD, REDUCE_DIM if REDUCE_DIM > 0 else None
                    )
                logger.info(
                    f"[INTERPRET] Pruned embedding uuid={uuid}, details={details}"
                )

                downstream_message = {
                    "uuid": uuid,
                    "tokens": tokens,
                    "pruned_embedding": pruned_embedding,
                    "pruning_details": details,
                    "timestamp": datetime.utcnow().isoformat(),
                }

                publish(INTERPRET_CHANNEL, downstream_message)
                logger.info(
                    f"[INTERPRET] Published data uuid={uuid} to '{INTERPRET_CHANNEL}'"
                )

            except Exception as e:
                interpret_errors.inc()
                logger.error(f"[INTERPRET] Error processing message: {e}")


def handle_shutdown(signal_received, frame):
    shutdown_flag.set()


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
threading.Thread(target=listener, daemon=True).start()


@app.get("/health")
def detailed_healthcheck():
    spacy_status = "ok"
    try:
        _ = nlp("test")
    except Exception as e:
        spacy_status = f"error: {str(e)}"

    return {
        "status": "active",
        "spacy": spacy_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
def healthcheck():
    return {"status": "interpret_service active"}


@app.post("/prune", response_model=PruneResponse)
async def prune(req: PruneRequest):
    if not req.embedding:
        raise HTTPException(status_code=400, detail="Embedding vector missing")
    try:
        with pruning_latency.time():
            pruned, details = prune_embedding(
                req.embedding, THRESHOLD, REDUCE_DIM if REDUCE_DIM > 0 else None
            )
    except Exception as e:
        interpret_errors.inc()
        raise HTTPException(status_code=400, detail=f"Failed to prune embedding: {e}")

    return PruneResponse(
        uuid=req.uuid,
        pruned_embedding=pruned,
        timestamp=datetime.utcnow(),
        details=details,
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
