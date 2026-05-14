from fastapi import WebSocket
from typing import Dict, Set
import asyncio
import json
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        logger.info("WebSocket connected", channel=channel, total=len(self.active_connections[channel]))

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        logger.info("WebSocket disconnected", channel=channel)

    async def broadcast(self, channel: str, message: dict):
        if channel not in self.active_connections:
            return
        dead = set()
        for ws in self.active_connections[channel]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections[channel].discard(ws)

    async def broadcast_all(self, message: dict):
        for channel in list(self.active_connections.keys()):
            await self.broadcast(channel, message)


manager = ConnectionManager()


async def redis_subscriber(redis_url: str):
    import redis.asyncio as aioredis
    r = aioredis.from_url(redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.psubscribe("sentinel:*")

    async for message in pubsub.listen():
        if message["type"] == "pmessage":
            channel = message["channel"].replace("sentinel:", "", 1)
            try:
                data = json.loads(message["data"])
                await manager.broadcast(channel, data)
                await manager.broadcast("all", data)
            except Exception as e:
                logger.error("WS broadcast error", error=str(e))
