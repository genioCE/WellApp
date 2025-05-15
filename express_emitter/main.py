from fastapi import FastAPI
from shared.redis_utils import subscribe, publish
from shared.logger import logger
import threading, json, time

app = FastAPI()

def listener():
    pubsub = subscribe("now_channel")
    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            logger.info(f"[EXPRESS] Emitting: {data}")
            publish("express_channel", data)

# Start background listener
threading.Thread(target=listener, daemon=True).start()

@app.get("/")
def root():
    return {"status": "express_emitter active"}

# Keep app alive
while True:
    time.sleep(60)
