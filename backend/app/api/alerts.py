from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertResponse, AlertUpdate

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    status: str | None = Query(None),
    alert_type: str | None = Query(None),
    table_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts with filtering and pagination."""
    query = select(Alert)

    if status:
        query = query.where(Alert.status == status)
    if alert_type:
        query = query.where(Alert.type == alert_type)
    if table_id:
        query = query.where(Alert.table_id == table_id)

    query = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: UUID,
    payload: AlertUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge, resolve, or snooze an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.utcnow()

    if payload.status == "acknowledged":
        alert.status = "acknowledged"
        alert.acknowledged_by = user.id
        alert.acknowledged_at = now
    elif payload.status == "resolved":
        alert.status = "resolved"
        alert.resolved_at = now
    elif payload.status == "snoozed":
        alert.status = "snoozed"
    elif payload.status == "open":
        alert.status = "open"
        alert.acknowledged_by = None
        alert.acknowledged_at = None
        alert.resolved_at = None
    else:
        raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")

    await db.flush()
    await db.refresh(alert)
    return alert
