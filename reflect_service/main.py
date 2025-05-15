from fastapi import FastAPI
from shared.redis_utils import subscribe, publish
from shared.logger import logger
import threading, json

app = FastAPI()

def truth_anchor(tokens):
    has_meaning = any(t.lower() in ["truth", "memory", "waking", "vision", "life", "soul"] for t in tokens)
    is_useful = len(tokens) > 2
    return has_meaning and is_useful

def listener():
    logger.info("[REFLECT] Starting listener on interpret_channel")
    try:
        pubsub = subscribe("interpret_channel")
        logger.info("[REFLECT] Subscribed successfully.")
        for message in pubsub.listen():
            logger.info(f"[REFLECT] Received raw message: {message}")
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    tokens = data.get("tokens", [])
                    logger.info(f"[REFLECT] Reviewing Tokens: {tokens}")
                    if truth_anchor(tokens):
                        logger.info(f"[TRUTH] Validated as Meaningful and Useful.")
                        publish("reflect_channel", {"tokens": tokens, "truth": True})
                    else:
                        logger.info(f"[TRUTH] Rejected: Lacked meaning or utility.")
                except Exception as e:
                    logger.error(f"[REFLECT] Error processing message: {e}")
    except Exception as e:
        logger.error(f"[REFLECT] Failed to subscribe: {e}")

threading.Thread(target=listener, daemon=True).start()

@app.get("/")
def healthcheck():
    return {"status": "reflect_service active"}

# RUN FASTAPI PROPERLY
import uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
