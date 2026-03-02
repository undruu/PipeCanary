from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectionCreate(BaseModel):
    type: str = Field(..., description="Warehouse type: snowflake, bigquery, databricks")
    name: str = Field(..., max_length=255)
    credentials: dict = Field(..., description="Warehouse-specific credential fields")
    config: dict | None = Field(None, description="Optional config (warehouse, database, schema defaults)")


class ConnectionResponse(BaseModel):
    id: UUID
    org_id: UUID
    type: str
    name: str
    status: str
    config: dict | None
    last_tested_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectionUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    credentials: dict | None = Field(None, description="Updated credential fields")
    config: dict | None = Field(None, description="Updated config fields")


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    error_detail: str | None = None
    tested_at: datetime
