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


class SnapshotLine(BaseModel):
    """Input line containing a sentence and metadata."""

    sentence: str
    timestamp: str
    source: str
    well_id: str


class InterpretRequest(BaseModel):
    """Request body for the /interpret endpoint."""

    lines: List[SnapshotLine]


class InterpretResponseLine(SnapshotLine):
    """Parsed interpretation of a single line."""

    subject: Optional[str] = None
    verb: Optional[str] = None
    object: Optional[str] = None
    tags: List[str] = []
