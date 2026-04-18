import asyncio
import json
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = structlog.get_logger(__name__)


class ConnectionManager:
    """WebSocket 연결을 관리합니다."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("websocket_connected", total=len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info("websocket_disconnected", total=len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """모든 연결된 클라이언트에 메시지를 전송합니다."""
        disconnected = []
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


@router.websocket("/live-feed")
async def websocket_live_feed(websocket: WebSocket) -> None:
    """실시간 방문 피드를 WebSocket으로 스트리밍합니다."""
    await manager.connect(websocket)
    try:
        # Ping/Pong keepalive (30초 간격)
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # keepalive ping
                await websocket.send_json({"type": "ping"})
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.warning("websocket_error", error=str(e))
    finally:
        manager.disconnect(websocket)


async def broadcast_visit_event(event: dict[str, Any]) -> None:
    """방문 이벤트를 모든 WebSocket 클라이언트에 브로드캐스트합니다."""
    await manager.broadcast({"type": "visit", "data": event})
