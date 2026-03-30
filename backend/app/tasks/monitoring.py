import asyncio
import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anomaly.detector import AnomalyDetector
from app.celery_app import celery_app
from app.config import settings
from app.connectors import get_connector_for_connection
from app.database import task_session
from app.models.alert import Alert
from app.models.check_result import CheckResult
from app.models.connection import Connection
from app.models.monitored_table import MonitoredTable
from app.models.notification_config import NotificationConfig
from app.monitoring.schema_engine import SchemaEngine
from app.notifications.email import EmailNotifier
from app.notifications.slack import SlackNotifier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Bridge async coroutines into synchronous Celery tasks."""
    return asyncio.run(coro)


async def _load_table_with_connection(
    db: AsyncSession, table_id: str | UUID
) -> tuple[MonitoredTable, Connection]:
    """Load a MonitoredTable and its parent Connection, or raise."""
    result = await db.execute(
        select(MonitoredTable).where(MonitoredTable.id == str(table_id))
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise ValueError(f"MonitoredTable {table_id} not found")

    result = await db.execute(
        select(Connection).where(Connection.id == table.connection_id)
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        raise ValueError(f"Connection {table.connection_id} not found")

    return table, connection


async def _send_notifications(
    db: AsyncSession,
    connection: Connection,
    alert: Alert,
    table: MonitoredTable,
) -> None:
    """Look up active notification configs for the org and dispatch alerts."""
    result = await db.execute(
        select(NotificationConfig).where(
            NotificationConfig.org_id == connection.org_id,
            NotificationConfig.is_active.is_(True),
        )
    )
    configs = result.scalars().all()

    if not configs:
        logger.info("No active notification configs for org %s", connection.org_id)

    alert_data = {
        "type": alert.type,
        "table_name": f"{table.schema_name}.{table.table_name}",
        "severity": alert.severity,
        "details": alert.details_json,
    }

    for nc in configs:
        if nc.channel == "slack":
            notifier = SlackNotifier(nc.destination)
            await notifier.send_alert(alert_data)
        elif nc.channel == "email":
            notifier = EmailNotifier(nc.destination)
            await notifier.send_alert(alert_data)

    # Also send to the global Slack webhook if configured
    if settings.slack_webhook_url:
        notifier = SlackNotifier(settings.slack_webhook_url)
        await notifier.send_alert(alert_data)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.monitoring.run_scheduled_checks")
def run_scheduled_checks():
    """Run all scheduled data quality checks.

    This is the main Celery beat task that:
    1. Finds all active monitored tables due for a check
    2. Dispatches individual check tasks for each table
    """
    logger.info("Starting scheduled check run")
    _run_async(_dispatch_scheduled_checks())
    logger.info("Scheduled check run complete")


# Map check_frequency values to the minimum interval between checks.
FREQUENCY_INTERVALS: dict[str, timedelta] = {
    "hourly": timedelta(hours=1),
    "every_6h": timedelta(hours=6),
    "every_12h": timedelta(hours=12),
    "daily": timedelta(hours=24),
    "weekly": timedelta(weeks=1),
}


def _is_table_due(table: MonitoredTable, last_check_at: datetime | None, now: datetime) -> bool:
    """Return True if *table* is due for its next check run."""
    interval = FREQUENCY_INTERVALS.get(table.check_frequency)
    if interval is None:
        # Unknown frequency — treat like "daily" as a safe default
        interval = FREQUENCY_INTERVALS["daily"]

    if last_check_at is None:
        # Never checked before — always due
        return True

    return (now - last_check_at) >= interval


async def _dispatch_scheduled_checks():
    async with task_session() as db:
        result = await db.execute(
            select(MonitoredTable).where(MonitoredTable.is_active.is_(True))
        )
        tables = result.scalars().all()

        now = datetime.utcnow()
        dispatched = 0

        for table in tables:
            # Find the most recent check result for this table
            last_result = await db.execute(
                select(CheckResult.measured_at)
                .where(CheckResult.table_id == table.id)
                .order_by(CheckResult.measured_at.desc())
                .limit(1)
            )
            row = last_result.first()
            last_check_at = row[0] if row else None

            if not _is_table_due(table, last_check_at, now):
                logger.debug(
                    "Skipping %s.%s (frequency=%s, last_check=%s)",
                    table.schema_name,
                    table.table_name,
                    table.check_frequency,
                    last_check_at,
                )
                continue

            table_id = str(table.id)
            run_schema_check.delay(table_id)
            run_row_count_check.delay(table_id)
            run_null_rate_check.delay(table_id)
            run_cardinality_check.delay(table_id)
            dispatched += 1

        logger.info("Dispatched checks for %d tables", dispatched)


@celery_app.task(
    name="app.tasks.monitoring.run_schema_check",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def run_schema_check(self, table_id: str):
    """Run schema drift detection for a single table.

    1. Load the monitored table and its connection
    2. Instantiate the appropriate warehouse connector
    3. Use SchemaEngine.detect_drift() to compare against last snapshot
    4. If drift detected, create alert and send notification
    """
    logger.info("Running schema check for table %s", table_id)
    try:
        _run_async(_do_schema_check(table_id))
    except Exception as exc:
        logger.exception("Schema check failed for table %s", table_id)
        raise self.retry(exc=exc)


async def _do_schema_check(table_id: str):
    async with task_session() as db:
        try:
            table, connection = await _load_table_with_connection(db, table_id)
            connector = get_connector_for_connection(connection)

            alert = await SchemaEngine.detect_drift(db, connector, table)

            if alert is not None:
                logger.info(
                    "Schema drift detected for %s.%s",
                    table.schema_name,
                    table.table_name,
                )
                await _send_notifications(db, connection, alert, table)

            await db.commit()
        except Exception:
            await db.rollback()
            raise


@celery_app.task(
    name="app.tasks.monitoring.run_row_count_check",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def run_row_count_check(self, table_id: str):
    """Run row count anomaly detection for a single table."""
    logger.info("Running row count check for table %s", table_id)
    try:
        _run_async(_do_row_count_check(table_id))
    except Exception as exc:
        logger.exception("Row count check failed for table %s", table_id)
        raise self.retry(exc=exc)


async def _do_row_count_check(table_id: str):
    async with task_session() as db:
        try:
            table, connection = await _load_table_with_connection(db, table_id)
            connector = get_connector_for_connection(connection)
            full_table_name = f"{table.schema_name}.{table.table_name}"

            # 1. Get current row count from the warehouse
            current_count = await connector.get_row_count(full_table_name)

            # 2. Store as CheckResult
            check_result = CheckResult(
                table_id=table.id,
                check_type="row_count",
                column_name=None,
                value=float(current_count),
            )
            db.add(check_result)
            await db.flush()

            # 3. Fetch historical counts (14-day trailing window, excluding the one we just inserted)
            cutoff = datetime.utcnow() - timedelta(days=14)
            history_result = await db.execute(
                select(CheckResult.value)
                .where(
                    CheckResult.table_id == table.id,
                    CheckResult.check_type == "row_count",
                    CheckResult.column_name.is_(None),
                    CheckResult.measured_at >= cutoff,
                    CheckResult.id != check_result.id,
                )
                .order_by(CheckResult.measured_at.asc())
            )
            historical_counts = [row[0] for row in history_result.all()]

            # 4. Run anomaly detection
            anomaly = AnomalyDetector.detect_row_count_anomaly(
                current_count=float(current_count),
                historical_counts=historical_counts,
            )

            # 5. If anomaly, create Alert and send notification
            if anomaly.is_anomaly:
                alert = Alert(
                    table_id=table.id,
                    type="row_count",
                    severity="warning",
                    status="open",
                    details_json={
                        "current_value": anomaly.current_value,
                        "baseline_mean": anomaly.baseline_mean,
                        "baseline_std": anomaly.baseline_std,
                        "z_score": anomaly.z_score,
                        "message": anomaly.message,
                    },
                )
                db.add(alert)
                await db.flush()
                logger.info(
                    "Row count anomaly detected for %s: %s",
                    full_table_name,
                    anomaly.message,
                )
                await _send_notifications(db, connection, alert, table)

            await db.commit()
        except Exception:
            await db.rollback()
            raise


@celery_app.task(
    name="app.tasks.monitoring.run_null_rate_check",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def run_null_rate_check(self, table_id: str):
    """Run null rate anomaly detection for a single table."""
    logger.info("Running null rate check for table %s", table_id)
    try:
        _run_async(_do_null_rate_check(table_id))
    except Exception as exc:
        logger.exception("Null rate check failed for table %s", table_id)
        raise self.retry(exc=exc)


async def _do_null_rate_check(table_id: str):
    async with task_session() as db:
        try:
            table, connection = await _load_table_with_connection(db, table_id)
            connector = get_connector_for_connection(connection)
            full_table_name = f"{table.schema_name}.{table.table_name}"

            # 1. Get current schema to know which columns to check
            columns_info = await connector.get_schema(full_table_name)
            column_names = [col["name"] for col in columns_info]
            if not column_names:
                logger.info("No columns found for %s, skipping null rate check", full_table_name)
                return

            # 2. Get null counts and row count from the warehouse
            null_counts = await connector.get_null_counts(full_table_name, column_names)
            row_count = await connector.get_row_count(full_table_name)

            if row_count == 0:
                logger.info("Table %s is empty, skipping null rate check", full_table_name)
                return

            # 3. Calculate null rates and store as CheckResults
            new_result_ids = []
            for col_name in column_names:
                null_count = null_counts.get(col_name, 0)
                null_rate = null_count / row_count

                check_result = CheckResult(
                    table_id=table.id,
                    check_type="null_rate",
                    column_name=col_name,
                    value=null_rate,
                )
                db.add(check_result)
                await db.flush()
                new_result_ids.append(check_result.id)

            # 4. For each column, fetch 7-day historical rates and detect anomalies
            cutoff = datetime.utcnow() - timedelta(days=7)
            anomalies_found = []

            for col_name in column_names:
                null_rate = null_counts.get(col_name, 0) / row_count

                history_result = await db.execute(
                    select(CheckResult.value)
                    .where(
                        CheckResult.table_id == table.id,
                        CheckResult.check_type == "null_rate",
                        CheckResult.column_name == col_name,
                        CheckResult.measured_at >= cutoff,
                        CheckResult.id.notin_(new_result_ids),
                    )
                    .order_by(CheckResult.measured_at.asc())
                )
                historical_rates = [row[0] for row in history_result.all()]

                anomaly = AnomalyDetector.detect_null_rate_anomaly(
                    current_rate=null_rate,
                    historical_rates=historical_rates,
                )

                if anomaly.is_anomaly:
                    anomalies_found.append((col_name, anomaly))

            # 5. Create a single alert per table if any column has anomalies
            if anomalies_found:
                column_details = {}
                for col_name, anomaly in anomalies_found:
                    column_details[col_name] = {
                        "current_rate": anomaly.current_value,
                        "baseline_mean": anomaly.baseline_mean,
                        "pct_change": anomaly.pct_change,
                        "message": anomaly.message,
                    }

                alert = Alert(
                    table_id=table.id,
                    type="null_rate",
                    severity="warning",
                    status="open",
                    details_json={
                        "columns_affected": len(anomalies_found),
                        "column_details": column_details,
                    },
                )
                db.add(alert)
                await db.flush()
                logger.info(
                    "Null rate anomaly detected for %s in %d column(s)",
                    full_table_name,
                    len(anomalies_found),
                )
                await _send_notifications(db, connection, alert, table)

            await db.commit()
        except Exception:
            await db.rollback()
            raise


@celery_app.task(
    name="app.tasks.monitoring.run_cardinality_check",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def run_cardinality_check(self, table_id: str):
    """Run cardinality anomaly detection for a single table."""
    logger.info("Running cardinality check for table %s", table_id)
    try:
        _run_async(_do_cardinality_check(table_id))
    except Exception as exc:
        logger.exception("Cardinality check failed for table %s", table_id)
        raise self.retry(exc=exc)


async def _do_cardinality_check(table_id: str):
    async with task_session() as db:
        try:
            table, connection = await _load_table_with_connection(db, table_id)
            connector = get_connector_for_connection(connection)
            full_table_name = f"{table.schema_name}.{table.table_name}"

            # 1. Get current schema to know which columns to check
            columns_info = await connector.get_schema(full_table_name)
            column_names = [col["name"] for col in columns_info]
            if not column_names:
                logger.info("No columns found for %s, skipping cardinality check", full_table_name)
                return

            # 2. Get cardinality (distinct counts) from the warehouse
            cardinality_counts = await connector.get_cardinality(full_table_name, column_names)

            # 3. Store as CheckResults
            new_result_ids = []
            for col_name in column_names:
                distinct_count = cardinality_counts.get(col_name, 0)

                check_result = CheckResult(
                    table_id=table.id,
                    check_type="cardinality",
                    column_name=col_name,
                    value=float(distinct_count),
                )
                db.add(check_result)
                await db.flush()
                new_result_ids.append(check_result.id)

            # 4. For each column, fetch 14-day historical cardinality and detect anomalies
            cutoff = datetime.utcnow() - timedelta(days=14)
            anomalies_found = []

            for col_name in column_names:
                current_value = float(cardinality_counts.get(col_name, 0))

                history_result = await db.execute(
                    select(CheckResult.value)
                    .where(
                        CheckResult.table_id == table.id,
                        CheckResult.check_type == "cardinality",
                        CheckResult.column_name == col_name,
                        CheckResult.measured_at >= cutoff,
                        CheckResult.id.notin_(new_result_ids),
                    )
                    .order_by(CheckResult.measured_at.asc())
                )
                historical_counts = [row[0] for row in history_result.all()]

                anomaly = AnomalyDetector.detect_cardinality_anomaly(
                    current_count=current_value,
                    historical_counts=historical_counts,
                )

                if anomaly.is_anomaly:
                    anomalies_found.append((col_name, anomaly))

            # 5. Create a single alert per table if any column has anomalies
            if anomalies_found:
                column_details = {}
                for col_name, anomaly in anomalies_found:
                    column_details[col_name] = {
                        "current_value": anomaly.current_value,
                        "baseline_mean": anomaly.baseline_mean,
                        "baseline_std": anomaly.baseline_std,
                        "z_score": anomaly.z_score,
                        "message": anomaly.message,
                    }

                alert = Alert(
                    table_id=table.id,
                    type="cardinality",
                    severity="warning",
                    status="open",
                    details_json={
                        "columns_affected": len(anomalies_found),
                        "column_details": column_details,
                    },
                )
                db.add(alert)
                await db.flush()
                logger.info(
                    "Cardinality anomaly detected for %s in %d column(s)",
                    full_table_name,
                    len(anomalies_found),
                )
                await _send_notifications(db, connection, alert, table)

            await db.commit()
        except Exception:
            await db.rollback()
            raise
