from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MonitorTableItem(BaseModel):
    schema_name: str
    table_name: str
    check_frequency: str = "daily"


class MonitorTablesRequest(BaseModel):
    connection_id: UUID
    tables: list[MonitorTableItem] = Field(..., min_length=1)


class MonitoredTableResponse(BaseModel):
    id: UUID
    connection_id: UUID
    schema_name: str
    table_name: str
    check_frequency: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SchemaColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool


class TableHealthResponse(BaseModel):
    table_id: UUID
    schema_name: str
    table_name: str
    latest_row_count: float | None = None
    latest_schema: list[SchemaColumnInfo] | None = None
    open_alerts_count: int = 0
    last_checked_at: datetime | None = None
