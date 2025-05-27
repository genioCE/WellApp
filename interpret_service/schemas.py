from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PruneRequest(BaseModel):
    uuid: str
    embedding: List[float]
    metadata: Optional[dict] = None

class PruneResponse(BaseModel):
    uuid: str
    pruned_embedding: List[float]
    timestamp: datetime
    details: dict
