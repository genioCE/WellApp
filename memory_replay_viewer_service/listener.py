# listeners.py
from shared.redis_utils import subscribe
from shared.logger import logger
from storage import add_replay
from schemas import MemoryEntry
import json

def memory_listener():
    pubsub = subscribe("memory_replay_channel")
    logger.info("[VIEWER] Subscribed to memory_replay_channel")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            data = json.loads(message["data"])
            entry = MemoryEntry(**data)
            add_replay(entry)
            logger.info(f"[VIEWER] Captured replay: {entry.timestamp}")
        except json.JSONDecodeError as e:
            logger.error(f"[VIEWER] JSON decode error: {e}")
        except Exception as e:
            logger.error(f"[VIEWER] General error: {e}")
