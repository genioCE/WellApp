from fastapi import FastAPI
from pydantic import BaseModel
from shared.redis_utils import subscribe, publish
from shared.logger import logger
from shared.config import (
    QDRANT_HOST,
    QDRANT_PORT,
    PGHOST,
    PGPORT,
    PGUSER,
    PGPASSWORD,
    PGDATABASE,
)
import threading
import json
import time
import os
import asyncpg
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import openai

app = FastAPI()

MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
COLLECTION = "genio_memory"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DATABASE_URL = f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
pg_pool: asyncpg.Pool | None = None

MEMORY_LOG = "/app/memory_log.jsonl"
CHAT_LOG = "/app/chat_log.jsonl"


class ChatRequest(BaseModel):
    """Input schema for the /chat endpoint."""

    well_id: str
    question: str
    persona: str


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize PostgreSQL connection pool."""
    global pg_pool
    pg_pool = await asyncpg.create_pool(DATABASE_URL)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Close PostgreSQL connection pool."""
    if pg_pool:
        await pg_pool.close()


def load_memory(filter_truth=True):
    if not os.path.exists(MEMORY_LOG):
        return []
    with open(MEMORY_LOG, "r") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    if filter_truth:
        return [e for e in entries if e.get("truth") is True]
    return entries


def listener():
    pubsub = subscribe("replay_channel")
    logger.info("[REPLAY] Subscribed to replay_channel")
    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"])
                cmd = data.get("command", "")
                if cmd == "replay":
                    logger.info("[REPLAY] Command received: replay")
                    entries = load_memory(filter_truth=True)
                    for entry in entries:
                        publish("memory_replay_channel", entry)
                        logger.info(f"[REPLAY] Emitted memory: {entry}")
                        time.sleep(0.5)  # Simulate temporal replay
            except Exception as e:
                logger.error(f"[REPLAY] Error processing message: {e}")


threading.Thread(target=listener, daemon=True).start()


@app.get("/replay/search")
def search_memory(query: str, well_id: str, top_k: int = 5):
    """Perform semantic search across stored memory vectors."""
    vector = model.encode(query).tolist()
    results = qdrant_client.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=top_k,
        query_filter=Filter(
            must=[FieldCondition(key="well_id", match=MatchValue(value=well_id))]
        ),
    )
    return [
        {
            "text": r.payload.get("text"),
            "source": r.payload.get("source"),
            "timestamp_or_page": r.payload.get("timestamp", r.payload.get("page")),
            "anomaly_or_importance": r.payload.get(
                "anomaly", r.payload.get("important", False)
            ),
            "vector_id": r.id,
        }
        for r in results
    ]


@app.get("/replay/timeline")
async def replay_timeline(well_id: str, source: str | None = None):
    """Return chronological replay of memory events for a well."""
    assert pg_pool is not None
    query = "SELECT text, timestamp_or_page, anomaly_or_importance, loop_stage, vector_id FROM memory_log WHERE well_id=$1"
    params = [well_id]
    if source:
        query += " AND source=$2"
        params.append(source)
    query += " ORDER BY timestamp_or_page"
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    return [dict(row) for row in rows]


@app.post("/chat")
async def chat(req: ChatRequest):
    """Answer a question using memory context and GPT-4o."""

    # Fetch related memory vectors
    vector = model.encode(req.question).tolist()
    results = qdrant_client.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=20,
        query_filter=Filter(
            must=[FieldCondition(key="well_id", match=MatchValue(value=req.well_id))]
        ),
    )

    # Aggregate memory until token budget reached (~6k tokens)
    MAX_TOKENS = 6000
    tokens = 0
    context: list[str] = []
    for r in results:
        text = r.payload.get("text", "")
        tcount = len(text.split())
        if tokens + tcount > MAX_TOKENS:
            break
        tokens += tcount
        context.append(text)

    # Build prompt with persona guidance
    prompt_lines = [
        f"You are a helpful {req.persona}.",
        "Use only the following memory facts to answer.",
        "If information is missing, say so and suggest the next action.",
    ]
    for i, c in enumerate(context):
        prompt_lines.append(f'Memory {i+1}: "{c}"')
    prompt_lines.append(f"Question: {req.question}")
    prompt = "\n".join(prompt_lines)

    openai.api_key = OPENAI_API_KEY
    completion = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = completion.choices[0].message["content"].strip()

    total_tokens = len(prompt.split()) + len(answer.split())
    cost = total_tokens / 1000 * 0.01
    logger.info(
        f"[CHAT] question={req.question} tokens={total_tokens} cost_est=${cost:.4f}"
    )
    logger.info(f"[CHAT] answer={answer}")

    try:
        with open(CHAT_LOG, "a") as f:
            f.write(
                json.dumps(
                    {
                        "well_id": req.well_id,
                        "question": req.question,
                        "answer": answer,
                        "tokens": total_tokens,
                    }
                )
                + "\n"
            )
    except Exception as e:  # pragma: no cover - file may not be writable
        logger.error(f"[CHAT] failed to log interaction: {e}")

    return {"answer": answer, "tokens": total_tokens, "estimated_cost": cost}


@app.get("/")
def healthcheck():
    return {"status": "replay_memory_service active"}


import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
