"""Pydantic schemas for the Reflect service."""

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


class ReflectRequest(BaseModel):
    """Input model containing interpreted sentences."""

    sentences: List[str]


class ReflectResponse(BaseModel):
    """Analysis result for a single event."""

    timestamp: str
    event: str
    confirmed_cause: Optional[str] = None
    next_question: str
