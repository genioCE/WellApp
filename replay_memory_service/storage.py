# storage.py
import os
import json
from schemas import MemoryEntry
from typing import List

MEMORY_LOG = "/app/memory_log.jsonl"

def load_memory(filter_truth: bool = True) -> List[MemoryEntry]:
    if not os.path.exists(MEMORY_LOG):
        return []
    with open(MEMORY_LOG, "r") as f:
        entries = [MemoryEntry(**json.loads(line)) for line in f if line.strip()]
    if filter_truth:
        return [entry for entry in entries if entry.truth]
    return entries
