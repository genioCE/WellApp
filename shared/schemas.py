from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NowSignal(BaseModel):
    timestamp: datetime
    source: str
    content: str

class ExpressedSignal(NowSignal):
    enriched: Optional[dict] = None
