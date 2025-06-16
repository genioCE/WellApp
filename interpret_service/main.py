from fastapi import FastAPI, HTTPException
from shared.redis_utils import subscribe, publish
from interpret_worker import listen_for_signals
from shared.logger import logger
import threading
import json
import spacy
import os
from datetime import datetime
from typing import List
from schemas import (
    PruneRequest,
    PruneResponse,
    InterpretRequest,
    InterpretResponseLine,
    SnapshotLine,
)
from pruning import prune_embedding
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Histogram, Counter
import openai
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
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SKIP_THREADS = os.getenv("INTERPRET_SKIP_THREADS") == "1"

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

                # ✅ NEW: publish to memory_replay_channel
                replay_message = {
                    "uuid": uuid,
                    "timestamp": downstream_message["timestamp"],
                    "tokens": tokens,
                    "weight": 1.0,
                    "tags": ["interpreted"],
                }
                publish("memory_replay_channel", replay_message)
                logger.info(
                    f"[INTERPRET] Published replay to 'memory_replay_channel': {replay_message}"
                )

            except Exception as e:
                interpret_errors.inc()
                logger.error(f"[INTERPRET] Error processing message: {e}")


def handle_shutdown(signal_received, frame):
    shutdown_flag.set()


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
if not SKIP_THREADS:
    threading.Thread(target=listener, daemon=True).start()
    threading.Thread(target=listen_for_signals, daemon=True).start()


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


def _chunks(items: List[str], size: int = 10) -> List[List[str]]:
    """Return items in consecutive batches."""

    return [items[i : i + size] for i in range(0, len(items), size)]


def extract_svo(lines: List[SnapshotLine]) -> List[dict]:
    """Call GPT-4o to parse sentences into subject, verb, object, and tags."""

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    openai.api_key = OPENAI_API_KEY
    sentences = [l.sentence for l in lines]
    results: List[dict] = []
    for batch in _chunks(sentences):
        prompt = (
            "For each numbered sentence, return JSON with subject, verb, object, "
            "and a short list of tags. Respond with a JSON array in the same order."\
            "\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(batch))
        )
        try:
            resp = openai.ChatCompletion.create(
                model=OPENAI_MODEL, messages=[{"role": "user", "content": prompt}]
            )
            data = json.loads(resp.choices[0].message["content"])
        except Exception as e:  # pragma: no cover - network issues
            interpret_errors.inc()
            logger.error(f"[INTERPRET] GPT extraction failed: {e}")
            data = [{} for _ in batch]
        if not isinstance(data, list):
            data = [{} for _ in batch]
        results.extend(data)
    return results


@app.post("/interpret", response_model=List[InterpretResponseLine])
async def interpret(req: InterpretRequest) -> List[InterpretResponseLine]:
    """Return subject, verb, object, and tags for each sentence."""

    if not req.lines:
        raise HTTPException(status_code=400, detail="No lines provided")

    parsed = extract_svo(req.lines)
    enriched: List[InterpretResponseLine] = []
    for line, info in zip(req.lines, parsed):
        enriched.append(
            InterpretResponseLine(
                sentence=line.sentence,
                timestamp=line.timestamp,
                source=line.source,
                well_id=line.well_id,
                subject=info.get("subject"),
                verb=info.get("verb"),
                object=info.get("object"),
                tags=info.get("tags", []),
            )
        )
    return enriched


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
