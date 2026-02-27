from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.alert import Alert
from app.models.check_result import CheckResult
from app.models.monitored_table import MonitoredTable
from app.models.schema_snapshot import SchemaSnapshot
from app.models.user import User
from app.schemas.table import (
    VALID_FREQUENCIES,
    MonitoredTableResponse,
    MonitorTablesRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
    TableHealthResponse,
)

router = APIRouter(tags=["tables"])


@router.post("/tables/monitor", response_model=list[MonitoredTableResponse], status_code=201)
async def add_monitored_tables(
    payload: MonitorTablesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add tables to monitoring."""
    tables = []
    for item in payload.tables:
        table = MonitoredTable(
            connection_id=payload.connection_id,
            schema_name=item.schema_name,
            table_name=item.table_name,
            check_frequency=item.check_frequency,
        )
        db.add(table)
        tables.append(table)

    await db.flush()
    for t in tables:
        await db.refresh(t)
    return tables


@router.get("/tables/{table_id}/health", response_model=TableHealthResponse)
async def get_table_health(
    table_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get health summary: latest schema, row count, null rates, cardinality."""
    result = await db.execute(select(MonitoredTable).where(MonitoredTable.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Monitored table not found")

    # Latest schema snapshot
    snapshot_result = await db.execute(
        select(SchemaSnapshot)
        .where(SchemaSnapshot.table_id == table_id)
        .order_by(SchemaSnapshot.captured_at.desc())
        .limit(1)
    )
    latest_snapshot = snapshot_result.scalar_one_or_none()

    # Latest row count
    row_count_result = await db.execute(
        select(CheckResult)
        .where(CheckResult.table_id == table_id, CheckResult.check_type == "row_count")
        .order_by(CheckResult.measured_at.desc())
        .limit(1)
    )
    latest_row_count = row_count_result.scalar_one_or_none()

    # Open alerts count
    alerts_count_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.table_id == table_id, Alert.status == "open")
    )
    open_alerts = alerts_count_result.scalar()

    return TableHealthResponse(
        table_id=table.id,
        schema_name=table.schema_name,
        table_name=table.table_name,
        latest_row_count=latest_row_count.value if latest_row_count else None,
        latest_schema=latest_snapshot.columns_json if latest_snapshot else None,
        open_alerts_count=open_alerts or 0,
        last_checked_at=latest_row_count.measured_at if latest_row_count else None,
    )


@router.get("/tables/{table_id}/schema/history")
async def get_schema_history(
    table_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get schema change history for a table."""
    result = await db.execute(
        select(SchemaSnapshot)
        .where(SchemaSnapshot.table_id == table_id)
        .order_by(SchemaSnapshot.captured_at.desc())
        .limit(50)
    )
    snapshots = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "columns": s.columns_json,
            "captured_at": s.captured_at.isoformat() if s.captured_at else None,
        }
        for s in snapshots
    ]


# ---------------------------------------------------------------------------
# Scheduling configuration
# ---------------------------------------------------------------------------


@router.get("/tables/{table_id}/schedule", response_model=ScheduleResponse)
async def get_table_schedule(
    table_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the scheduling configuration for a monitored table."""
    result = await db.execute(select(MonitoredTable).where(MonitoredTable.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Monitored table not found")
    return table


@router.patch("/tables/{table_id}/schedule", response_model=ScheduleResponse)
async def update_table_schedule(
    table_id: UUID,
    payload: ScheduleUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the check frequency and/or active status for a monitored table."""
    result = await db.execute(select(MonitoredTable).where(MonitoredTable.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Monitored table not found")

    if payload.check_frequency is not None:
        if payload.check_frequency not in VALID_FREQUENCIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid frequency '{payload.check_frequency}'. "
                f"Must be one of: {', '.join(sorted(VALID_FREQUENCIES))}",
            )
        table.check_frequency = payload.check_frequency

    if payload.is_active is not None:
        table.is_active = payload.is_active

    await db.flush()
    await db.refresh(table)
    return table
