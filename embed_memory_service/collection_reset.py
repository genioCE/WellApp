from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

client = QdrantClient(url="http://localhost:6333")
client.recreate_collection(
    collection_name="genio_embeddings",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)
print("Qdrant collection explicitly reset with dimension 384.")
