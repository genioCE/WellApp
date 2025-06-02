# storage.py
from schemas import MemoryEntry
from typing import List
import threading

latest_replays: List[MemoryEntry] = []
lock = threading.Lock()

def add_replay(entry: MemoryEntry, limit: int = 50):
    with lock:
        latest_replays.append(entry)
        if len(latest_replays) > limit:
            latest_replays.pop(0)

def get_latest_replays() -> List[MemoryEntry]:
    with lock:
        return list(reversed(latest_replays))
