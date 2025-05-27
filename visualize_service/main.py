from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from shared.logger import logger
from schemas import VisualizeRequest, VisualizeResponse
from visualization import generate_visualization
from shared.redis_utils import subscribe, publish
import threading
import json
import asyncio  # <-- explicitly import this
import uvicorn


app = FastAPI(title="Genio Visualize Service")
app.mount("/static", StaticFiles(directory="."), name="static")

async def process_message(data):
    req = VisualizeRequest(
        uuid=data["uuid"],
        anchored_embedding=data["anchored_embedding"],
        method=data.get("method", "pca"),
        dimensions=data.get("dimensions", 2)
    )
    try:
        path, vis_type = await generate_visualization(
            req.anchored_embedding, req.method, req.dimensions
        )
        url = f"/static/{path}"
        response = {
            "uuid": req.uuid,
            "visualization_url": url,
            "visualization_type": vis_type,
            "timestamp": datetime.utcnow().isoformat(),
            "anchored_embedding": req.anchored_embedding  # <-- explicitly added
        }
        publish("visualize_channel", response)
        logger.info(f"[VISUALIZE] Published visualization uuid={req.uuid} to 'visualize_channel'")
    except Exception as e:
        logger.error(f"[VISUALIZE] Error generating visualization: {e}")

def listener():
    pubsub = subscribe("reflect_channel")
    logger.info("[VISUALIZE] Subscribed to 'reflect_channel'")
    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"])
                asyncio.run(process_message(data))
            except Exception as e:
                logger.error(f"[VISUALIZE] Failed to process message: {e}")

# Start Redis listener explicitly in background
threading.Thread(target=listener, daemon=True).start()

@app.post("/visualize", response_model=VisualizeResponse)
async def visualize(req: VisualizeRequest):
    logger.info(f"[VISUALIZE] HTTP Request: {req.uuid}")
    try:
        path, vis_type = await generate_visualization(req.anchored_embedding, req.method, req.dimensions)
        url = f"/static/{path}"
        return VisualizeResponse(
            uuid=req.uuid,
            visualization_url=url,
            visualization_type=vis_type,
            timestamp=datetime.utcnow()
        )
    except ValueError as e:
        logger.error(f"[VISUALIZE] Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[VISUALIZE] Error generating visualization: {e}")
        raise HTTPException(status_code=500, detail="Visualization failed")

@app.get("/")
async def healthcheck():
    return {"status": "visualize_service active"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
