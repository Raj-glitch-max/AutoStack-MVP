from __future__ import annotations

import asyncio
import uuid
from contextlib import suppress
from typing import Dict, Set, Tuple

from fastapi import WebSocket
from sqlalchemy import select

from .db import AsyncSessionLocal
from .models import DeploymentLog


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: Dict[uuid.UUID, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_tasks: Dict[Tuple[uuid.UUID, WebSocket], asyncio.Task] = {}
        self._disconnect_events: Dict[Tuple[uuid.UUID, WebSocket], asyncio.Event] = {}
        self._ping_interval = 25

    async def register(self, deployment_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        key = (deployment_id, websocket)
        async with self._lock:
            connections = self._connections.setdefault(deployment_id, set())
            connections.add(websocket)
            event = asyncio.Event()
            self._disconnect_events[key] = event
            task = asyncio.create_task(self._heartbeat_loop(deployment_id, websocket))
            self._heartbeat_tasks[key] = task

    async def unregister(self, deployment_id: uuid.UUID, websocket: WebSocket) -> None:
        key = (deployment_id, websocket)
        async with self._lock:
            connections = self._connections.get(deployment_id)
            if connections and websocket in connections:
                connections.remove(websocket)
                if not connections:
                    self._connections.pop(deployment_id, None)
            task = self._heartbeat_tasks.pop(key, None)
            event = self._disconnect_events.pop(key, None)
        if event and not event.is_set():
            event.set()
        if task and task is not asyncio.current_task():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def wait_for_disconnect(self, deployment_id: uuid.UUID, websocket: WebSocket) -> None:
        key = (deployment_id, websocket)
        async with self._lock:
            event = self._disconnect_events.get(key)
        if not event:
            return
        await event.wait()

    async def send_history(self, deployment_id: uuid.UUID, websocket: WebSocket) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DeploymentLog)
                .where(DeploymentLog.deployment_id == deployment_id)
                .order_by(DeploymentLog.timestamp.asc())
            )
            logs = [log.message for log in result.scalars().all()]
        await websocket.send_json({"type": "history", "logs": logs})

    async def broadcast_log(self, deployment_id: uuid.UUID, line: str) -> None:
        await self._broadcast(deployment_id, {"type": "log", "line": line})

    async def broadcast_event(self, deployment_id: uuid.UUID, payload: dict) -> None:
        await self._broadcast(deployment_id, payload)

    async def _broadcast(self, deployment_id: uuid.UUID, payload: dict) -> None:
        async with self._lock:
            connections = list(self._connections.get(deployment_id, set()))
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                await self._signal_disconnect(deployment_id, websocket)

    async def _signal_disconnect(self, deployment_id: uuid.UUID, websocket: WebSocket) -> None:
        key = (deployment_id, websocket)
        async with self._lock:
            event = self._disconnect_events.get(key)
        if event and not event.is_set():
            event.set()

    async def _heartbeat_loop(self, deployment_id: uuid.UUID, websocket: WebSocket) -> None:
        try:
            while True:
                await asyncio.sleep(self._ping_interval)
                await websocket.send_json({"type": "ping"})
        except Exception:
            await self._signal_disconnect(deployment_id, websocket)


ws_manager = WebSocketManager()


async def broadcast_deployment_event(deployment_id: uuid.UUID, message: dict) -> None:
    await ws_manager.broadcast_event(deployment_id, message)
