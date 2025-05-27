from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
import os
import psycopg2
from shared.logger import logger

ALLOWED_EXTENSIONS = {'.txt', '.md', '.json'}
STORAGE_ROOT = '/tmp/ingested_files'

app = FastAPI(title="Genio Text File Ingestor")


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'postgres'),
        port=os.getenv('PGPORT', '5432'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', 'postgres'),
        dbname=os.getenv('PGDATABASE', 'genio')
    )


def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ingested_files (
                id UUID PRIMARY KEY,
                filename TEXT,
                filetype TEXT,
                timestamp TIMESTAMP
            )
            """
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"DB init failed: {e}")


@app.on_event("startup")
def startup_event():
    init_db()
    os.makedirs(STORAGE_ROOT, exist_ok=True)


class IngestResponse(BaseModel):
    id: str
    filename: str
    filetype: str
    timestamp: datetime
    preview: str


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content_bytes = await file.read()
    try:
        text = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = content_bytes.decode('utf-8', errors='replace')

    uid = str(uuid4())
    ts = datetime.utcnow()
    dir_path = os.path.join(STORAGE_ROOT, ts.strftime('%Y%m%d_%H%M%S'))
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, f"{uid}{ext}")
    with open(file_path, 'wb') as f:
        f.write(content_bytes)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ingested_files (id, filename, filetype, timestamp) VALUES (%s, %s, %s, %s)",
            (uid, file.filename, ext.lstrip('.'), ts)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log to DB: {e}")

    preview = text[:200]
    logger.info(f"[NOW_FILE] Ingested {file.filename} as {uid}")
    return IngestResponse(id=uid, filename=file.filename, filetype=ext.lstrip('.'), timestamp=ts, preview=preview)


@app.get("/")
def healthcheck():
    return {"status": "now_file_ingestor active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
