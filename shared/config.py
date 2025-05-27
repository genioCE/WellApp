import os

# Redis settings explicitly defined
REDIS_HOST = os.getenv("REDIS_HOST", "genio_redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# PostgreSQL settings (optional example for clarity)
PGHOST = os.getenv("PGHOST", "postgres")
PGPORT = int(os.getenv("PGPORT", 5432))
PGUSER = os.getenv("PGUSER", "user")
PGPASSWORD = os.getenv("PGPASSWORD", "password")
PGDATABASE = os.getenv("PGDATABASE", "database")

# Qdrant settings (optional example for clarity)
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
