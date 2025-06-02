# schemas.py
from pydantic import BaseModel
from typing import List, Optional

class MemoryEntry(BaseModel):
    timestamp: str
    tokens: List[str]
    truth: Optional[bool] = None
