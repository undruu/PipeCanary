from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    id: UUID
    table_id: UUID
    type: str
    severity: str
    status: str
    details_json: dict
    acknowledged_by: UUID | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertUpdate(BaseModel):
    status: str = Field(..., description="New status: acknowledged, resolved, snoozed")
