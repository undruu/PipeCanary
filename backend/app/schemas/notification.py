from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationConfigCreate(BaseModel):
    channel: str = Field(..., description="Notification channel: slack, email")
    destination: str = Field(..., description="Webhook URL or email address")
    filters: dict | None = Field(None, description="Severity and type filters")


class NotificationConfigResponse(BaseModel):
    id: UUID
    org_id: UUID
    channel: str
    destination: str
    filters: dict | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
