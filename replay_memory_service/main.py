from fastapi import FastAPI
from shared.redis_utils import subscribe, publish
from shared.logger import logger
import threading, json, time
import os

app = FastAPI()
MEMORY_LOG = "/app/memory_log.jsonl"

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

@app.get("/")
def healthcheck():
    return {"status": "replay_memory_service active"}

import uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
