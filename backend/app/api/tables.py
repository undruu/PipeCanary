from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.alert import Alert
from app.models.check_result import CheckResult
from app.models.connection import Connection
from app.models.monitored_table import MonitoredTable
from app.models.organization import Organization
from app.models.schema_snapshot import SchemaSnapshot
from app.models.user import User
from app.schemas.table import (
    VALID_FREQUENCIES,
    CheckResultResponse,
    DashboardSummary,
    MonitoredTableResponse,
    MonitorTablesRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
    TableHealthResponse,
    TableListItem,
)

router = APIRouter(tags=["tables"])


# ---------------------------------------------------------------------------
# Helper: resolve the user's org
# ---------------------------------------------------------------------------

async def _get_user_org(user: User, db: AsyncSession) -> Organization | None:
    result = await db.execute(
        select(Organization).where(Organization.owner_id == user.id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# List all monitored tables
# ---------------------------------------------------------------------------


@router.get("/tables", response_model=list[TableListItem])
async def list_monitored_tables(
    connection_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all monitored tables for the user's org with basic health info."""
    org = await _get_user_org(user, db)
    if not org:
        return []

    # Base query: join MonitoredTable → Connection to scope by org
    query = (
        select(MonitoredTable)
        .join(Connection, MonitoredTable.connection_id == Connection.id)
        .where(Connection.org_id == org.id)
        .options(selectinload(MonitoredTable.connection))
    )

    if connection_id is not None:
        query = query.where(MonitoredTable.connection_id == connection_id)
    if is_active is not None:
        query = query.where(MonitoredTable.is_active == is_active)

    query = query.order_by(MonitoredTable.created_at.desc())
    result = await db.execute(query)
    tables = result.scalars().all()

    items: list[TableListItem] = []
    for t in tables:
        # Open alerts count
        alerts_q = await db.execute(
            select(func.count(Alert.id)).where(
                Alert.table_id == t.id, Alert.status == "open"
            )
        )
        open_count = alerts_q.scalar() or 0

        # Latest row count
        rc_q = await db.execute(
            select(CheckResult)
            .where(CheckResult.table_id == t.id, CheckResult.check_type == "row_count")
            .order_by(CheckResult.measured_at.desc())
            .limit(1)
        )
        latest_rc = rc_q.scalar_one_or_none()

        items.append(
            TableListItem(
                id=t.id,
                connection_id=t.connection_id,
                connection_name=t.connection.name,
                schema_name=t.schema_name,
                table_name=t.table_name,
                check_frequency=t.check_frequency,
                is_active=t.is_active,
                open_alerts_count=open_count,
                latest_row_count=latest_rc.value if latest_rc else None,
                last_checked_at=latest_rc.measured_at if latest_rc else None,
                created_at=t.created_at,
            )
        )

    return items


# ---------------------------------------------------------------------------
# Check results history (for sparklines / charts)
# ---------------------------------------------------------------------------


@router.get(
    "/tables/{table_id}/check-results",
    response_model=list[CheckResultResponse],
)
async def get_check_results(
    table_id: UUID,
    check_type: str = Query("row_count"),
    days: int = Query(14, le=90),
    column_name: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return check results for a table within a time window."""
    since = datetime.utcnow() - timedelta(days=days)
    query = (
        select(CheckResult)
        .where(
            CheckResult.table_id == table_id,
            CheckResult.check_type == check_type,
            CheckResult.measured_at >= since,
        )
        .order_by(CheckResult.measured_at.asc())
    )
    if column_name is not None:
        query = query.where(CheckResult.column_name == column_name)

    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate counts for the dashboard cards."""
    org = await _get_user_org(user, db)
    if not org:
        return DashboardSummary()

    # Active connections
    conn_q = await db.execute(
        select(func.count(Connection.id)).where(
            Connection.org_id == org.id, Connection.status == "active"
        )
    )
    active_connections = conn_q.scalar() or 0

    # Monitored tables
    table_q = await db.execute(
        select(func.count(MonitoredTable.id))
        .join(Connection, MonitoredTable.connection_id == Connection.id)
        .where(Connection.org_id == org.id)
    )
    monitored_tables = table_q.scalar() or 0

    # Open alerts (total, critical, warning)
    alert_base = (
        select(Alert)
        .join(MonitoredTable, Alert.table_id == MonitoredTable.id)
        .join(Connection, MonitoredTable.connection_id == Connection.id)
        .where(Connection.org_id == org.id, Alert.status == "open")
    )

    total_q = await db.execute(
        select(func.count(Alert.id)).select_from(alert_base.subquery())
    )
    open_alerts = total_q.scalar() or 0

    crit_q = await db.execute(
        select(func.count(Alert.id))
        .join(MonitoredTable, Alert.table_id == MonitoredTable.id)
        .join(Connection, MonitoredTable.connection_id == Connection.id)
        .where(
            Connection.org_id == org.id,
            Alert.status == "open",
            Alert.severity == "critical",
        )
    )
    critical_alerts = crit_q.scalar() or 0

    warn_q = await db.execute(
        select(func.count(Alert.id))
        .join(MonitoredTable, Alert.table_id == MonitoredTable.id)
        .join(Connection, MonitoredTable.connection_id == Connection.id)
        .where(
            Connection.org_id == org.id,
            Alert.status == "open",
            Alert.severity == "warning",
        )
    )
    warning_alerts = warn_q.scalar() or 0

    # Last check timestamp
    last_check_q = await db.execute(
        select(func.max(CheckResult.measured_at))
        .join(MonitoredTable, CheckResult.table_id == MonitoredTable.id)
        .join(Connection, MonitoredTable.connection_id == Connection.id)
        .where(Connection.org_id == org.id)
    )
    last_check_at = last_check_q.scalar()

    return DashboardSummary(
        active_connections=active_connections,
        monitored_tables=monitored_tables,
        open_alerts=open_alerts,
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        last_check_at=last_check_at,
    )


# ---------------------------------------------------------------------------
# Existing endpoints
# ---------------------------------------------------------------------------


@router.post("/tables/monitor", response_model=list[MonitoredTableResponse], status_code=201)
async def add_monitored_tables(
    payload: MonitorTablesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add tables to monitoring, skipping any that are already monitored."""
    # Find which tables are already monitored for this connection
    existing_result = await db.execute(
        select(MonitoredTable.schema_name, MonitoredTable.table_name).where(
            MonitoredTable.connection_id == payload.connection_id
        )
    )
    existing_keys = {(row.schema_name, row.table_name) for row in existing_result}

    tables = []
    for item in payload.tables:
        if (item.schema_name, item.table_name) in existing_keys:
            continue
        table = MonitoredTable(
            connection_id=payload.connection_id,
            schema_name=item.schema_name,
            table_name=item.table_name,
            check_frequency=item.check_frequency,
        )
        db.add(table)
        tables.append(table)

    if tables:
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


# ---------------------------------------------------------------------------
# Manual check trigger
# ---------------------------------------------------------------------------


@router.post("/tables/{table_id}/run-checks", status_code=202)
async def run_checks_now(
    table_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dispatch all check tasks (schema, row count, null rate, cardinality) for a table immediately."""
    result = await db.execute(select(MonitoredTable).where(MonitoredTable.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Monitored table not found")

    from app.tasks.monitoring import (
        run_cardinality_check,
        run_null_rate_check,
        run_row_count_check,
        run_schema_check,
    )

    tid = str(table_id)
    run_schema_check.delay(tid)
    run_row_count_check.delay(tid)
    run_null_rate_check.delay(tid)
    run_cardinality_check.delay(tid)

    return {"detail": "Checks dispatched", "table_id": tid}
