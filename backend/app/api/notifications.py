from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.notification_config import NotificationConfig
from app.models.organization import Organization
from app.models.user import User
from app.schemas.notification import NotificationConfigCreate, NotificationConfigResponse

router = APIRouter(tags=["notifications"])


@router.put("/notifications/config", response_model=NotificationConfigResponse)
async def update_notification_config(
    payload: NotificationConfigCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update notification preferences."""
    result = await db.execute(select(Organization).where(Organization.owner_id == user.id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=400, detail="No organization found for user")

    # Upsert: find existing config for this channel or create new
    existing_result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.org_id == org.id,
            NotificationConfig.channel == payload.channel,
        )
    )
    config = existing_result.scalar_one_or_none()

    if config:
        config.destination = payload.destination
        config.filters = payload.filters
    else:
        config = NotificationConfig(
            org_id=org.id,
            channel=payload.channel,
            destination=payload.destination,
            filters=payload.filters,
        )
        db.add(config)

    await db.flush()
    await db.refresh(config)
    return config
