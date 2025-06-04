from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timedelta
import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from loguru import logger
import shutil
from prometheus_fastapi_instrumentator import Instrumentator

from shared.schemas import NowSignal
from shared.redis_utils import publish

# ────────────────────────────────────────────
# Configuration Constants
# ────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'.txt', '.md', '.json'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
STORAGE_ROOT = '/tmp/ingested_files'

# ────────────────────────────────────────────
# FastAPI App Setup
# ────────────────────────────────────────────
app = FastAPI(title="Genio NOW Ingestor Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to ['http://localhost:5173'] for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

# ────────────────────────────────────────────
# PostgreSQL Connection Pool
# ────────────────────────────────────────────
pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=os.getenv('PGHOST', 'postgres'),
    port=os.getenv('PGPORT', '5432'),
    user=os.getenv('PGUSER', 'postgres'),
    password=os.getenv('PGPASSWORD', 'postgres'),
    dbname=os.getenv('PGDATABASE', 'genio')
)

def get_db_connection():
    return pool.getconn()

def put_db_connection(conn):
    pool.putconn(conn)

# ────────────────────────────────────────────
# Startup: Init DB + Storage Dir
# ────────────────────────────────────────────
@app.on_event("startup")
def startup_event():
    init_db()
    os.makedirs(STORAGE_ROOT, exist_ok=True)

def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ingested_files (
                    id UUID PRIMARY KEY,
                    filename TEXT,
                    filetype TEXT,
                    timestamp TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("[NOW] Database initialized successfully")
    except Exception as e:
        logger.error(f"[NOW] DB initialization failed: {e}")
    finally:
        put_db_connection(conn)

# ────────────────────────────────────────────
# Models
# ────────────────────────────────────────────
class IngestResponse(BaseModel):
    id: str
    filename: str
    filetype: str
    timestamp: datetime
    preview: str

class NowSignal(BaseModel):
    timestamp: datetime
    source: str
    content: str

# ────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────
@app.post("/memory/ingest")
def memory_ingest_fallback(text: str = Body(..., embed=True)):
    signal = NowSignal(
        timestamp=datetime.utcnow(),
        source="frontend",
        content=text
    )
    logger.info("[NOW] Received memory snapshot via /memory/ingest", text=text)
    publish("now_channel", signal.dict())
    return {"status": "published", "text": text}

@app.post("/ingest")
def ingest_signal(signal: NowSignal):
    logger.info("[NOW] Received NowSignal", signal=signal.dict())
    publish("now_channel", signal.dict())
    return {"status": "published"}

@app.post("/ingest-file", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"[NOW_FILE] Unsupported file type: {ext}")
        raise HTTPException(status_code=400, detail="Unsupported file type")

    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        logger.warning(f"[NOW_FILE] File too large: {file.filename}")
        raise HTTPException(status_code=413, detail="File too large")

    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = content_bytes.decode("utf-8", errors="replace")

    uid = str(uuid4())
    ts = datetime.utcnow()
    dir_path = os.path.join(STORAGE_ROOT, ts.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, f"{uid}{ext}")

    with open(file_path, "wb") as f:
        f.write(content_bytes)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ingested_files (id, filename, filetype, timestamp) VALUES (%s, %s, %s, %s)",
                (uid, file.filename, ext.lstrip('.'), ts)
            )
            conn.commit()
            logger.info("[NOW_FILE] Logged file ingestion to DB", uuid=uid)
    except Exception as e:
        logger.error(f"[NOW_FILE] Failed to log to DB: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during DB logging")
    finally:
        put_db_connection(conn)

    background_tasks.add_task(cleanup_old_files)

    preview = text[:200]
    logger.info("[NOW_FILE] Ingested file", file_name=file.filename, uuid=uid, timestamp=ts.isoformat())
    return IngestResponse(
        id=uid,
        filename=file.filename,
        filetype=ext.lstrip('.'),
        timestamp=ts,
        preview=preview
    )

@app.get("/health")
def detailed_healthcheck():
    try:
        conn = get_db_connection()
        conn.close()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"[NOW] Health check failed: {db_status}")

    return {
        "status": "active",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# ────────────────────────────────────────────
# Background Cleanup
# ────────────────────────────────────────────
def cleanup_old_files(days: int = 7):
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    for folder in os.listdir(STORAGE_ROOT):
        folder_path = os.path.join(STORAGE_ROOT, folder)
        if os.path.isdir(folder_path):
            try:
                folder_time = datetime.strptime(folder, "%Y%m%d_%H%M%S")
                if folder_time < cutoff_time:
                    shutil.rmtree(folder_path)
                    logger.info(f"[NOW] Removed old folder: {folder_path}")
            except ValueError:
                continue

# ────────────────────────────────────────────
# Uvicorn Entry (optional for local dev)
# ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
