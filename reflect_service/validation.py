from typing import List, Tuple
from datetime import datetime
import os
import numpy as np

ANCHOR_THRESHOLD = float(os.getenv("ANCHOR_THRESHOLD", 0.5))

async def validate_embedding(embedding: List[float]) -> Tuple[List[float], str, str]:
    if not embedding:
        return embedding, "rejected", "empty embedding"

    array = np.array(embedding, dtype=float)
    anchor = np.zeros_like(array)
    diff = np.linalg.norm(array - anchor)

    if diff <= ANCHOR_THRESHOLD:
        status = "valid"
        anchored = array
        summary = "within threshold"
    elif diff <= ANCHOR_THRESHOLD * 2:
        status = "adjusted"
        anchored = array * (ANCHOR_THRESHOLD / diff)
        summary = "scaled to threshold"
    else:
        status = "rejected"
        anchored = array
        summary = "exceeded threshold"

    return anchored.tolist(), status, summary
