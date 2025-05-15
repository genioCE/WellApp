from fastapi import FastAPI
from shared.redis_utils import subscribe
from shared.logger import logger
import threading, json
from datetime import datetime
import os
import duckdb
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance, CollectionStatus
from sentence_transformers import SentenceTransformer

app = FastAPI()

# Init DuckDB
DUCKDB_PATH = "/app/genio_memory.duckdb"
conn = duckdb.connect(DUCKDB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        id UUID,
        timestamp TIMESTAMP,
        tokens TEXT[],
        truth BOOLEAN
    )
""")

# Init Qdrant
qdrant = QdrantClient(host="qdrant", port=6333)
COLLECTION_NAME = "genio_memory"
if COLLECTION_NAME not in [c.name for c in qdrant.get_collections().collections]:
    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

# Init Embedding Model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Shared
MEMORY_LOG = "/app/memory_log.jsonl"

def write_to_memory(entry):
    os.makedirs(os.path.dirname(MEMORY_LOG), exist_ok=True)
    with open(MEMORY_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logger.info(f"[MEMORY] Embedded (flat log): {entry}")

def write_to_duckdb(entry):
    import uuid
    uid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO memory VALUES (?, ?, ?, ?)",
        (uid, entry["timestamp"], entry["tokens"], entry["truth"])
    )
    logger.info(f"[MEMORY] Embedded (DuckDB): {uid}")

def write_to_qdrant(entry):
    import uuid
    uid = str(uuid.uuid4())
    sentence = " ".join(entry["tokens"])
    embedding = model.encode(sentence).tolist()
    point = PointStruct(id=uid, vector=embedding, payload=entry)
    qdrant.upsert(collection_name=COLLECTION_NAME, points=[point])
    logger.info(f"[MEMORY] Embedded (Qdrant): {uid}")

def listener():
    pubsub = subscribe("reflect_channel")
    logger.info("[EMBED] Subscribed to reflect_channel")
    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "tokens": data.get("tokens", []),
                "truth": data.get("truth", False)
            }
            write_to_memory(entry)
            write_to_duckdb(entry)
            write_to_qdrant(entry)

threading.Thread(target=listener, daemon=True).start()

@app.get("/")
def healthcheck():
    return {"status": "embed_memory_service + DuckDB/Qdrant active"}

import uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
