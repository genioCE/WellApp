from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AnchorRequest(BaseModel):
    uuid: str
    pruned_embedding: List[float]
    metadata: Optional[dict] = None

class AnchorResponse(BaseModel):
    uuid: str
    anchored_embedding: List[float]
    status: str
    timestamp: datetime
    summary: Optional[str] = None
