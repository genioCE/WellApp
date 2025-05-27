import os
import json
import asyncio
import asyncpg
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
import logging
import uuid

logger = logging.getLogger("genio.embed.database")


DATABASE_URL = f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "genio_embeddings")
TARGET_EMBEDDING_DIM = 384

class Database:
    def __init__(self) -> None:
        self.pg_pool: asyncpg.Pool | None = None
        self.qdrant: QdrantClient | None = None
        self.collection_initialized = False

    async def connect(self) -> None:
        self.pg_pool = await asyncpg.create_pool(DATABASE_URL)
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    id SERIAL PRIMARY KEY,
                    uuid TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    metadata JSONB
                )
                """
            )
        self.qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        logger.info("Database connections established")

    async def ensure_collection(self, size: int) -> None:
        if self.collection_initialized:
            return
        assert self.qdrant is not None
        collections = [c.name for c in self.qdrant.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self.qdrant.recreate_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )
        self.collection_initialized = True


    async def store_embedding(
        self, uuid_str: str, vector: List[float], metadata: Dict[str, Any], timestamp
    ) -> int:
        assert self.pg_pool is not None
        assert self.qdrant is not None

        # Explicit padding to fixed dimension
        if len(vector) < TARGET_EMBEDDING_DIM:
            vector += [0.0] * (TARGET_EMBEDDING_DIM - len(vector))
        elif len(vector) > TARGET_EMBEDDING_DIM:
            vector = vector[:TARGET_EMBEDDING_DIM]

        await self.ensure_collection(TARGET_EMBEDDING_DIM)

        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO embeddings(uuid, timestamp, metadata) VALUES($1,$2,$3) RETURNING id",
                uuid_str,
                timestamp,
                json.dumps(metadata),
            )
        metadata_id = row["id"]

        # Validate UUID explicitly
        try:
            valid_uuid = str(uuid.UUID(uuid_str))
        except ValueError:
            valid_uuid = str(uuid.uuid4())

        payload = {"metadata_id": metadata_id, **metadata}

        def upsert():
            self.qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(id=valid_uuid, vector=vector, payload=payload)],
            )

        await asyncio.to_thread(upsert)
        return metadata_id
