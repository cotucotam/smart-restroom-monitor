from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import Alert, Device, User
from schemas import AlertOut
from services.auth_service import require_operator_or_admin
from services.state_service import manager

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=List[AlertOut])
def get_alerts(
    unack_only: bool = Query(True),
    limit: int = Query(100),
    db: Session = Depends(get_db),
    user: User = Depends(require_operator_or_admin)
):
    query = db.query(Alert)
    if unack_only:
        query = query.filter(Alert.acknowledged_at == None)
    
    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()
    results = []

    for al in alerts:
        dev = al.device
        toilet = dev.gateway.toilet if (dev and dev.gateway) else None
        floor = toilet.floor if toilet else None
        terminal = floor.terminal if floor else None

        results.append({
            "id": al.id,
            "device_id": al.device_id,
            "device_label": dev.label if dev else f"Device #{al.device_id}",
            "toilet_id": toilet.id if toilet else 0,
            "toilet_name": toilet.name if toilet else "Không rõ",
            "floor_name": floor.name if floor else "Không rõ",
            "terminal_name": terminal.name if terminal else "Không rõ",
            "type": al.type,
            "created_at": al.created_at,
            "acknowledged_by": al.acknowledged_by,
            "acknowledged_at": al.acknowledged_at
        })

    return results

@router.post("/acknowledge-all")
async def acknowledge_all_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(require_operator_or_admin)
):
    unack_alerts = db.query(Alert).filter(Alert.acknowledged_at == None).all()
    count = len(unack_alerts)
    if count == 0:
        return {"status": "success", "count": 0, "message": "Không có cảnh báo nào chưa xử lý"}

    now = datetime.now(timezone.utc)
    for al in unack_alerts:
        al.acknowledged_by = user.username
        al.acknowledged_at = now
    db.commit()

    # Notify via WebSocket
    await manager.broadcast({
        "event": "ALERT_ACKNOWLEDGED",
        "data": {
            "all": True,
            "count": count,
            "acknowledged_by": user.username,
            "acknowledged_at": now.isoformat()
        }
    })

    return {
        "status": "success",
        "count": count,
        "message": f"Đã xác nhận nhanh tất cả {count} cảnh báo bởi {user.username}",
        "acknowledged_at": now.isoformat()
    }

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator_or_admin)
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")

    if alert.acknowledged_at is not None:
        return {"message": "Cảnh báo này đã được xác nhận trước đó", "acknowledged_by": alert.acknowledged_by}

    now = datetime.now(timezone.utc)
    alert.acknowledged_by = user.username
    alert.acknowledged_at = now
    db.commit()

    # Notify via WebSocket
    await manager.broadcast({
        "event": "ALERT_ACKNOWLEDGED",
        "data": {
            "alert_id": alert.id,
            "acknowledged_by": user.username,
            "acknowledged_at": now.isoformat()
        }
    })

    return {
        "status": "success",
        "message": f"Đã xác nhận cảnh báo bởi {user.username}",
        "acknowledged_at": now.isoformat()
    }
