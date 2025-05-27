from fastapi import FastAPI
from shared.logger import logger
from .routes import router

app = FastAPI(title="Genio REFLECT Service")

app.include_router(router)

@app.get("/")
async def healthcheck():
    return {"status": "reflect_service active"}
