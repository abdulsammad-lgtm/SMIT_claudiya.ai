import json
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.dependencies import ws_auth
from app.cache.redis_client import redis_client

logger = logging.getLogger(__name__)
router = APIRouter()

_active_connections: dict[str, list[WebSocket]] = {
    "dashboard": [],
    "transactions": [],
    "alerts": [],
}


async def broadcast(channel: str, message: dict):
    text = json.dumps(message)
    for ws in _active_connections.get(channel, [])[:]:
        try:
            await ws.send_text(text)
        except Exception:
            _active_connections[channel] = [
                w for w in _active_connections[channel] if w != ws
            ]


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket, token: str | None = Query(None)):
    user = await ws_auth(websocket, token)
    if not user:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    _active_connections["dashboard"].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("action") == "ping":
                await websocket.send_text(json.dumps({"action": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        _active_connections["dashboard"] = [
            w for w in _active_connections["dashboard"] if w != websocket
        ]


@router.websocket("/ws/transactions")
async def transactions_ws(websocket: WebSocket, token: str | None = Query(None)):
    user = await ws_auth(websocket, token)
    if not user:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    _active_connections["transactions"].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("action") == "ping":
                await websocket.send_text(json.dumps({"action": "pong"}))
            elif msg.get("action") == "subscribe":
                filters = msg.get("filters", {})
                await websocket.send_text(json.dumps({
                    "action": "subscribed",
                    "filters": filters,
                }))
    except WebSocketDisconnect:
        pass
    finally:
        _active_connections["transactions"] = [
            w for w in _active_connections["transactions"] if w != websocket
        ]


@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket, token: str | None = Query(None)):
    user = await ws_auth(websocket, token)
    if not user:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    _active_connections["alerts"].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("action") == "ping":
                await websocket.send_text(json.dumps({"action": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        _active_connections["alerts"] = [
            w for w in _active_connections["alerts"] if w != websocket
        ]


async def notify_new_transaction(txn_data: dict):
    await broadcast("dashboard", {
        "action": "new_transaction",
        "data": txn_data,
    })
    await broadcast("transactions", {
        "action": "new_transaction",
        "data": txn_data,
    })
    risk = txn_data.get("risk_score", 0)
    if risk > 50:
        await broadcast("alerts", {
            "action": "high_risk_alert",
            "data": txn_data,
        })
