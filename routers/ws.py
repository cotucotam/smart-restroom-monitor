from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.state_service import manager

router = APIRouter(tags=["websocket"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial welcome / handshake
        await websocket.send_json({"event": "CONNECTED", "message": "WebSocket connection established"})
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
