from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class VisualizeRequest(BaseModel):
    uuid: str
    anchored_embedding: List[float] = Field(..., description="Validated embedding vector")
    metadata: Optional[Dict] = None
    method: Optional[str] = Field("pca", description="Visualization method: pca or tsne")
    dimensions: Optional[int] = Field(2, description="Target dimension: 2 or 3")

class VisualizeResponse(BaseModel):
    uuid: str
    visualization_url: str
    visualization_type: str
    timestamp: datetime
