from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from starlette.responses import StreamingResponse

logger = logging.getLogger(__name__)

ws_router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.dashboard_connections: list[WebSocket] = []
        self.session_connections: dict[str, list[WebSocket]] = {}
        self._sse_queues: list[asyncio.Queue] = []

    async def connect_dashboard(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.dashboard_connections.append(websocket)

    async def connect_session(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.session_connections.setdefault(session_id, []).append(websocket)

    def disconnect_dashboard(self, websocket: WebSocket) -> None:
        try:
            self.dashboard_connections.remove(websocket)
        except ValueError:
            pass

    def disconnect_session(self, websocket: WebSocket, session_id: str) -> None:
        conns = self.session_connections.get(session_id, [])
        try:
            conns.remove(websocket)
        except ValueError:
            pass
        if not conns:
            self.session_connections.pop(session_id, None)

    async def broadcast_to_dashboard(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        for ws in self.dashboard_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_dashboard(ws)

        for q in list(self._sse_queues):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    async def send_to_session(self, session_id: str, message: dict[str, Any]) -> None:
        payload = json.dumps(message, default=str)
        conns = self.session_connections.get(session_id, [])
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_session(ws, session_id)

    def create_sse_queue(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._sse_queues.append(q)
        return q

    def remove_sse_queue(self, q: asyncio.Queue) -> None:
        try:
            self._sse_queues.remove(q)
        except ValueError:
            pass


manager = ConnectionManager()


@ws_router.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket) -> None:
    await manager.connect_dashboard(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Dashboard WS received: %s", data[:200])
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
    except Exception:
        manager.disconnect_dashboard(websocket)


@ws_router.websocket("/ws/session/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str) -> None:
    await manager.connect_session(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                msg = {"type": "text_input", "text": data}

            app = websocket.app
            pipeline_manager = getattr(app.state, "pipeline_manager", None)
            if pipeline_manager is None:
                await manager.send_to_session(session_id, {
                    "type": "error",
                    "content": "Agent pipeline not available",
                })
                continue

            text = msg.get("text", "")
            if not text:
                continue

            try:
                responses = await pipeline_manager.process_input(session_id, text)
                for resp in responses:
                    await manager.send_to_session(session_id, resp.model_dump())
            except Exception as exc:
                logger.exception("Pipeline error for session %s", session_id)
                await manager.send_to_session(session_id, {
                    "type": "error",
                    "content": f"Processing error: {exc}",
                })
    except WebSocketDisconnect:
        manager.disconnect_session(websocket, session_id)
    except Exception:
        manager.disconnect_session(websocket, session_id)


@ws_router.get("/api/events/dashboard")
async def sse_dashboard(request: Request) -> StreamingResponse:
    q = manager.create_sse_queue()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            manager.remove_sse_queue(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
