from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from shared.logger import logger
from schemas import VisualizeRequest, VisualizeResponse
from visualization import generate_visualization
import uvicorn

app = FastAPI(title="Genio Visualize Service")
app.mount("/static", StaticFiles(directory="."), name="static")

@app.post("/visualize", response_model=VisualizeResponse)
async def visualize(req: VisualizeRequest):
    logger.info(f"[VISUALIZE] Request: {req.uuid}")
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
