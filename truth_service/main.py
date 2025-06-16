import os
import json
import time
import uuid
from typing import Any, Dict, List, Tuple

import psycopg2
import redis
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from sentence_transformers import SentenceTransformer


REDIS_HOST = os.getenv("REDIS_HOST", "genio_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
TRUTH_CHANNEL = os.getenv("TRUTH_CHANNEL", "truth_channel")
EMBED_CHANNEL = os.getenv("EMBED_CHANNEL", "embed_channel")

PG_OPTS = dict(
    host=os.getenv("PGHOST", "postgres"),
    port=os.getenv("PGPORT", "5432"),
    user=os.getenv("PGUSER", "user"),
    password=os.getenv("PGPASSWORD", "password"),
    dbname=os.getenv("PGDATABASE", "database"),
)

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "genio_memory")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))


model = SentenceTransformer("all-MiniLM-L6-v2")
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def embed_text(text: str) -> List[float]:
    """Return 384-dim embedding for provided text."""
    return model.encode(text).tolist()


def fetch_rows(cursor: Any, table: str) -> List[Tuple[Any, ...]]:
    cursor.execute(
        f"SELECT id, well_id, timestamp, text, noun_phrases, anomaly, source_file FROM {table} WHERE embedded = false LIMIT %s",
        (BATCH_SIZE,),
    )
    return cursor.fetchall()


def fetch_wellfile(cursor: Any) -> List[Tuple[Any, ...]]:
    cursor.execute(
        "SELECT id, well_id, page, text, noun_phrases, important, source_file FROM reflected_wellfile WHERE embedded = false LIMIT %s",
        (BATCH_SIZE,),
    )
    return cursor.fetchall()


def mark_embedded(cursor: Any, table: str, ids: List[Any]) -> None:
    cursor.execute(
        f"UPDATE {table} SET embedded = true WHERE id = ANY(%s)",
        (ids,),
    )


def upsert_points(points: List[PointStruct]) -> None:
    qdrant.upsert(collection_name=QDRANT_COLLECTION, points=points)


def embed_reflected_scada(conn: Any) -> None:
    with conn.cursor() as cur:
        rows = fetch_rows(cur, "reflected_scada")
        if not rows:
            return
        points: List[PointStruct] = []
        ids: List[Any] = []
        for row in rows:
            row_id, well_id, ts, text, phrases, anomaly, src_file = row
            vector = embed_text(text)
            payload: Dict[str, Any] = {
                "well_id": well_id,
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
                "text": text,
                "noun_phrases": phrases,
                "anomaly": anomaly,
                "source_file": src_file,
                "source": "scada",
                "loop_stage": "truth",
            }
            points.append(
                PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)
            )
            ids.append(row_id)
        upsert_points(points)
        mark_embedded(cur, "reflected_scada", ids)
        conn.commit()
        redis_client.publish(
            EMBED_CHANNEL,
            json.dumps(
                {"event": "embed_ready", "well_id": rows[0][1], "source": "scada"}
            ),
        )


def embed_reflected_wellfile(conn: Any) -> None:
    with conn.cursor() as cur:
        rows = fetch_wellfile(cur)
        if not rows:
            return
        points: List[PointStruct] = []
        ids: List[Any] = []
        for row in rows:
            row_id, well_id, page, text, phrases, important, src_file = row
            vector = embed_text(text)
            payload: Dict[str, Any] = {
                "well_id": well_id,
                "page": page,
                "text": text,
                "noun_phrases": phrases,
                "important": important,
                "source_file": src_file,
                "source": "wellfile",
                "loop_stage": "truth",
            }
            points.append(
                PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)
            )
            ids.append(row_id)
        upsert_points(points)
        mark_embedded(cur, "reflected_wellfile", ids)
        conn.commit()
        redis_client.publish(
            EMBED_CHANNEL,
            json.dumps(
                {"event": "embed_ready", "well_id": rows[0][1], "source": "wellfile"}
            ),
        )


def listen() -> None:
    conn = psycopg2.connect(**PG_OPTS)
    pubsub = redis_client.pubsub()
    pubsub.subscribe(TRUTH_CHANNEL)
    for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            data = json.loads(message["data"])
        except json.JSONDecodeError:
            continue
        if data.get("event") != "truth_ready":
            continue
        source = data.get("source")
        if source == "scada":
            embed_reflected_scada(conn)
        elif source == "wellfile":
            embed_reflected_wellfile(conn)
        time.sleep(0.1)


if __name__ == "__main__":
    listen()
