from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from shared.redis_utils import subscribe
from shared.logger import logger
import threading
import json

app = FastAPI()
latest_replays = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def listener():
    try:
        pubsub = subscribe("memory_replay_channel")
        logger.info("[VIEWER] Subscribed to memory_replay_channel")
        for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                latest_replays.append(data)
                if len(latest_replays) > 50:
                    latest_replays.pop(0)
                logger.info(f"[VIEWER] Captured replay: {data}")
    except Exception as e:
        logger.error(f"[VIEWER] Listener failed: {e}")

@app.on_event("startup")
def start_listener_thread():
    threading.Thread(target=listener, daemon=True).start()

@app.get("/", response_class=HTMLResponse)
def view_replays():
    html = "<h1>Memory Replay Viewer</h1><ul>"
    for replay in reversed(latest_replays):
        html += f"<li><b>{replay.get('timestamp')}</b>: {', '.join(replay.get('tokens', []))}</li>"
    html += "</ul>"
    return html

@app.get("/memory/replay")
def get_latest_replays():
    """
    Returns the latest memory replays for frontend consumption.
    """
    logger.info(f"[VIEWER] Serving {len(latest_replays)} replays")
    return list(reversed(latest_replays))  # newest first

@app.get("/health")
def health():
    return {"status": "ok", "count": len(latest_replays)}
