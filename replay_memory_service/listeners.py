# listeners.py
from shared.redis_utils import subscribe, publish
from shared.logger import logger
from storage import load_memory
import json, time

def replay_listener():
    pubsub = subscribe("replay_channel")
    logger.info("[REPLAY] Subscribed to replay_channel")

    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            data = json.loads(message["data"])
            if data.get("command") == "replay":
                logger.info("[REPLAY] Command received: replay")
                entries = load_memory(filter_truth=True)
                for entry in entries:
                    publish("memory_replay_channel", entry.dict())
                    logger.info(f"[REPLAY] Emitted memory: {entry.timestamp}")
                    time.sleep(0.5)
        except json.JSONDecodeError as e:
            logger.error(f"[REPLAY] JSON decode error: {e}")
        except Exception as e:
            logger.error(f"[REPLAY] General error: {e}")
