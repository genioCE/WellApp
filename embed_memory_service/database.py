import os
import json
import asyncio
import asyncpg
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
import logging

logger = logging.getLogger("genio.embed.database")

DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql://postgres:postgres@postgres:5432/genio")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "genio_embeddings")

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
        self, uuid: str, vector: List[float], metadata: Dict[str, Any], timestamp
    ) -> int:
        assert self.pg_pool is not None
        assert self.qdrant is not None
        await self.ensure_collection(len(vector))
        async with self.pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO embeddings(uuid, timestamp, metadata) VALUES($1,$2,$3) RETURNING id",
                uuid,
                timestamp,
                json.dumps(metadata),
            )
        metadata_id = row["id"]

        payload = {"metadata_id": metadata_id, **metadata}

        def upsert():
            self.qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(id=uuid, vector=vector, payload=payload)],
            )

        await asyncio.to_thread(upsert)
        return metadata_id
