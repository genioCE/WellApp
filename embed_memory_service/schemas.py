from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class EmbedRequest(BaseModel):
    uuid: str
    anchored_embedding: List[float]
    metadata: Optional[Dict[str, Any]] = None

class EmbedResponse(BaseModel):
    uuid: str
    stored: bool
    timestamp: datetime
    metadata_id: Optional[int] = None
