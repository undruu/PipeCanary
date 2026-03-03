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


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

VALID_FREQUENCIES = {"hourly", "every_6h", "every_12h", "daily", "weekly"}


class ScheduleUpdateRequest(BaseModel):
    check_frequency: str | None = Field(
        None,
        description="Check frequency: hourly, every_6h, every_12h, daily, weekly",
    )
    is_active: bool | None = Field(None, description="Enable or disable monitoring")


class ScheduleResponse(BaseModel):
    id: UUID
    connection_id: UUID
    schema_name: str
    table_name: str
    check_frequency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# List tables with health summary
# ---------------------------------------------------------------------------


class TableListItem(BaseModel):
    id: UUID
    connection_id: UUID
    connection_name: str
    schema_name: str
    table_name: str
    check_frequency: str
    is_active: bool
    open_alerts_count: int = 0
    latest_row_count: float | None = None
    last_checked_at: datetime | None = None
    created_at: datetime


class CheckResultResponse(BaseModel):
    id: UUID
    table_id: UUID
    check_type: str
    column_name: str | None = None
    value: float
    measured_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------


class DashboardSummary(BaseModel):
    active_connections: int = 0
    monitored_tables: int = 0
    open_alerts: int = 0
    critical_alerts: int = 0
    warning_alerts: int = 0
    last_check_at: datetime | None = None
