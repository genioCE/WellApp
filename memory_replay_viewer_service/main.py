from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from shared.redis_utils import subscribe
from shared.logger import logger
from shared.config import QDRANT_HOST, QDRANT_PORT
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
import openai
import os
import threading
import json

app = FastAPI()
latest_replays = []

MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
COLLECTION = "genio_memory"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def listener():
    try:
        pubsub = subscribe("memory_replay_channel")
        logger.info("[VIEWER] Subscribed to memory_replay_channel")
        for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                latest_replays.append(data)
                if len(latest_replays) > 50:
                    latest_replays.pop(0)
                logger.info(f"[VIEWER] Captured replay: {data}")
    except Exception as e:
        logger.error(f"[VIEWER] Listener failed: {e}")


@app.on_event("startup")
def start_listener_thread():
    threading.Thread(target=listener, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def view_replays():
    html = "<h1>Memory Replay Viewer</h1><ul>"
    for replay in reversed(latest_replays):
        html += f"<li><b>{replay.get('timestamp')}</b>: {', '.join(replay.get('tokens', []))}</li>"
    html += "</ul>"
    return html


@app.get("/memory/replay")
def get_latest_replays():
    """
    Returns the latest memory replays for frontend consumption.
    """
    logger.info(f"[VIEWER] Serving {len(latest_replays)} replays")
    return list(reversed(latest_replays))  # newest first


@app.post("/chat")
async def chat(query: str, well_id: str):
    """Answer questions using memory context from Qdrant."""
    vector = model.encode(query).tolist()
    results = qdrant_client.search(
        collection_name=COLLECTION,
        query_vector=vector,
        limit=5,
        query_filter=Filter(
            must=[FieldCondition(key="well_id", match=MatchValue(value=well_id))]
        ),
    )
    context_lines = [
        f"Memory {i+1}: \"{r.payload.get('text','')}\"" for i, r in enumerate(results)
    ]
    prompt = "Context:\n\n" + "\n\n".join(context_lines)
    prompt += f'\n\nQuestion: "{query}"\nAnswer:'
    openai.api_key = OPENAI_API_KEY
    try:
        completion = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = completion.choices[0].message["content"].strip()
    except Exception as e:  # pragma: no cover - openai may fail
        logger.error(f"[VIEWER] OpenAI call failed: {e}")
        answer = "Error generating answer"
    excerpts = [r.payload.get("text") for r in results]
    return {"answer": answer, "sources": excerpts}


@app.get("/health")
def health():
    return {"status": "ok", "count": len(latest_replays)}
