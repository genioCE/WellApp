import json
import os
import threading
from typing import List

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import redis

from shared.logger import logger

# Environment configuration
REDIS_HOST = os.getenv("REDIS_HOST", "genio_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
PGHOST = os.getenv("PGHOST", "postgres")
PGPORT = int(os.getenv("PGPORT", 5432))
PGUSER = os.getenv("PGUSER", "user")
PGPASSWORD = os.getenv("PGPASSWORD", "password")
PGDATABASE = os.getenv("PGDATABASE", "database")

KEYWORDS = ["lease", "permit", "inspection", "abandonment", "test"]

stop_event = threading.Event()


def get_db_connection() -> psycopg2.extensions.connection:
    """Create a new PostgreSQL connection."""

    return psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        user=PGUSER,
        password=PGPASSWORD,
        dbname=PGDATABASE,
    )


def flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Add an ``anomaly`` column based on rolling statistics."""

    df = df.copy()
    mean_pressure = df["pressure"].rolling(window=10, min_periods=1).mean().shift(1)
    std_pressure = (
        df["pressure"].rolling(window=10, min_periods=1).std().shift(1).fillna(0)
    )
    mean_flow = df["flow_rate"].rolling(window=10, min_periods=1).mean().shift(1)
    std_flow = (
        df["flow_rate"].rolling(window=10, min_periods=1).std().shift(1).fillna(0)
    )

    anomaly = ((df["pressure"] - mean_pressure).abs() > 2 * std_pressure) | (
        (df["flow_rate"] - mean_flow).abs() > 2 * std_flow
    )

    df["anomaly"] = anomaly.fillna(False)
    return df


def contains_keywords(text: str, keywords: List[str]) -> bool:
    """Return ``True`` if any keyword appears in the given text."""

    lower = text.lower()
    return any(k in lower for k in keywords)


def reflect_scada() -> None:
    """Process unreflected SCADA rows and flag anomalies."""

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, well_id, timestamp, text, noun_phrases,
                       pressure, flow_rate, source_file
                FROM interpreted_scada
                WHERE reflected = false
                """
            )
            rows = cur.fetchall()

        if not rows:
            return

        columns = [
            "id",
            "well_id",
            "timestamp",
            "text",
            "noun_phrases",
            "pressure",
            "flow_rate",
            "source_file",
        ]
        df = pd.DataFrame(rows, columns=columns)
        df = flag_anomalies(df)

        records = [
            (
                row.id,
                row.well_id,
                row.timestamp,
                row.text,
                row.noun_phrases,
                bool(row.anomaly),
                row.source_file,
            )
            for row in df.itertuples(index=False)
        ]

        with conn.cursor() as cur:
            execute_batch(
                cur,
                """
                INSERT INTO reflected_scada (
                    id, well_id, timestamp, text, noun_phrases,
                    anomaly, source_file
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                records,
            )
            execute_batch(
                cur,
                "UPDATE interpreted_scada SET reflected = true WHERE id = %s",
                [(r[0],) for r in records],
            )
        conn.commit()
        logger.info("[REFLECTOR] Processed %d scada rows", len(records))
    except Exception as exc:
        logger.error("[REFLECTOR] reflect_scada failed: %s", exc)
    finally:
        conn.close()


def reflect_wellfile() -> None:
    """Process unreflected WELLFILE rows and flag important clauses."""

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, well_id, timestamp, text, noun_phrases, source_file
                FROM interpreted_wellfile
                WHERE reflected = false
                """
            )
            rows = cur.fetchall()

        if not rows:
            return

        records = []
        for row in rows:
            important = contains_keywords(row[3], KEYWORDS)
            records.append(
                (
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    important,
                    row[5],
                )
            )

        with conn.cursor() as cur:
            execute_batch(
                cur,
                """
                INSERT INTO reflected_wellfile (
                    id, well_id, timestamp, text, noun_phrases,
                    important, source_file
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                records,
            )
            execute_batch(
                cur,
                "UPDATE interpreted_wellfile SET reflected = true WHERE id = %s",
                [(r[0],) for r in records],
            )
        conn.commit()
        logger.info("[REFLECTOR] Processed %d wellfile rows", len(records))
    except Exception as exc:
        logger.error("[REFLECTOR] reflect_wellfile failed: %s", exc)
    finally:
        conn.close()


def listen_for_signals() -> None:
    """Listen for ``reflect_ready`` events on Redis."""

    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    pubsub = client.pubsub()
    pubsub.subscribe("reflect_channel")
    logger.info("[REFLECTOR] Subscribed to 'reflect_channel'")

    for message in pubsub.listen():
        if stop_event.is_set():
            break
        if message.get("type") != "message":
            continue
        try:
            payload = json.loads(message.get("data", "{}"))
        except json.JSONDecodeError as exc:
            logger.error("[REFLECTOR] JSON error: %s", exc)
            continue
        if payload.get("event") != "reflect_ready":
            continue

        source = payload.get("source")
        well_id = payload.get("well_id")
        if source == "scada":
            reflect_scada()
        elif source == "wellfile":
            reflect_wellfile()

        client.publish(
            "truth_channel",
            json.dumps({"event": "truth_ready", "well_id": well_id, "source": source}),
        )
        logger.info("[REFLECTOR] Published truth_ready for well %s", well_id)


def stop_listener() -> None:
    """Signal the listener thread to stop."""

    stop_event.set()
