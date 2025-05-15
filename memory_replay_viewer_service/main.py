from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from shared.redis_utils import subscribe
from shared.logger import logger
import threading, json

app = FastAPI()
latest_replays = []

def listener():
    pubsub = subscribe("memory_replay_channel")
    logger.info("[VIEWER] Subscribed to memory_replay_channel")
    for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            latest_replays.append(data)
            if len(latest_replays) > 50:
                latest_replays.pop(0)
            logger.info(f"[VIEWER] Captured replay: {data}")

@app.get("/", response_class=HTMLResponse)
def view_replays():
    html = "<h1>Memory Replay Viewer</h1><ul>"
    for replay in reversed(latest_replays):
        html += f"<li><b>{replay.get('timestamp')}</b>: {', '.join(replay.get('tokens', []))}</li>"
    html += "</ul>"
    return html

threading.Thread(target=listener, daemon=True).start()

import uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
