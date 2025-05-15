from fastapi import FastAPI
from shared.redis_utils import subscribe, publish  # <— ADD THIS
from shared.logger import logger
import threading, json
import spacy
import time

app = FastAPI()

# Load spaCy model safely
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    logger.error(f"Failed to load spaCy model: {e}")
    exit(1)

def listener():
    pubsub = subscribe("express_channel")
    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            doc = nlp(data["content"])
            tokens = [token.text for token in doc if not token.is_stop]
            logger.info(f"[INTERPRET] Parsed Tokens: {tokens}")
            data["tokens"] = tokens  # <— CRITICAL LINE
            publish("interpret_channel", data)  # <— ADD THIS

# Launch background listener
threading.Thread(target=listener, daemon=True).start()

@app.get("/")
def healthcheck():
    return {"status": "interpret_service active"}

while True:
    time.sleep(60)
