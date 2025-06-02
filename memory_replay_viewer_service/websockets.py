# websockets.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
from schemas import MemoryEntry
import asyncio
import json

active_connections: List[WebSocket] = []

async def notify_clients(entry: MemoryEntry):
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_text(entry.json())
        except Exception:
            disconnected.append(connection)

    for conn in disconnected:
        active_connections.remove(conn)

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        active_connections.remove(websocket)
