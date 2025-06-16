import os
import json
from typing import List
from datetime import datetime

import psycopg2
import redis
import spacy


REDIS_HOST = os.getenv("REDIS_HOST", "genio_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
INTERPRET_CHANNEL = os.getenv("INTERPRET_CHANNEL", "interpret_channel")
REFLECT_CHANNEL = os.getenv("REFLECT_CHANNEL", "reflect_channel")

PG_CONFIG = {
    "host": os.getenv("PGHOST", "postgres"),
    "port": os.getenv("PGPORT", "5432"),
    "user": os.getenv("PGUSER", "user"),
    "password": os.getenv("PGPASSWORD", "password"),
    "dbname": os.getenv("PGDATABASE", "database"),
}

nlp = spacy.load("en_core_web_sm")
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def extract_noun_phrases(text: str) -> List[str]:
    """Return a list of noun phrases from the provided text."""
    doc = nlp(text)
    return [chunk.text for chunk in doc.noun_chunks]


def get_db_connection():
    return psycopg2.connect(**PG_CONFIG)


def interpret_scada() -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, well_id, timestamp, pressure, flow_rate, source_file
                FROM snapshot_scada
                WHERE interpreted = false
                ORDER BY timestamp
                LIMIT 200
                """
            )
            rows = cur.fetchall()

            for row in rows:
                rec_id, well_id, ts, pressure, flow_rate, source_file = row
                ts_fmt = ts.strftime("%H:%M on %b %d")
                text = f"At {ts_fmt}, pressure was {pressure} psi and flow rate was {flow_rate} bbl/hr."
                noun_phrases = json.dumps(extract_noun_phrases(text))
                cur.execute(
                    """
                    INSERT INTO interpreted_scada (id, well_id, timestamp, text, noun_phrases, source_file)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (rec_id, well_id, ts, text, noun_phrases, source_file),
                )
                cur.execute(
                    "UPDATE snapshot_scada SET interpreted = true WHERE id = %s",
                    (rec_id,),
                )
        conn.commit()
    finally:
        conn.close()


def interpret_wellfile() -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, well_id, page, text, source_file
                FROM snapshot_wellfile
                WHERE interpreted = false
                ORDER BY id
                LIMIT 200
                """
            )
            rows = cur.fetchall()

            for row in rows:
                rec_id, well_id, page, text, source_file = row
                noun_phrases = json.dumps(extract_noun_phrases(text))
                cur.execute(
                    """
                    INSERT INTO interpreted_wellfile (id, well_id, page, text, noun_phrases, source_file)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (rec_id, well_id, page, text, noun_phrases, source_file),
                )
                cur.execute(
                    "UPDATE snapshot_wellfile SET interpreted = true WHERE id = %s",
                    (rec_id,),
                )
        conn.commit()
    finally:
        conn.close()


def listen_for_signals() -> None:
    pubsub = redis_client.pubsub()
    pubsub.subscribe(INTERPRET_CHANNEL)

    for message in pubsub.listen():
        if message.get("type") != "message":
            continue
        try:
            payload = json.loads(message["data"])
        except json.JSONDecodeError:
            continue

        if payload.get("event") == "interpret_ready":
            src = payload.get("source")
            well_id = payload.get("well_id")
            if src == "scada":
                interpret_scada()
            elif src == "wellfile":
                interpret_wellfile()
            redis_client.publish(
                REFLECT_CHANNEL,
                json.dumps(
                    {"event": "reflect_ready", "well_id": well_id, "source": src}
                ),
            )
