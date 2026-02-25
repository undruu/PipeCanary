from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import WarehouseConnector
from app.models.alert import Alert
from app.models.monitored_table import MonitoredTable
from app.models.schema_snapshot import SchemaSnapshot


class SchemaDiff:
    """Represents differences between two schema snapshots."""

    def __init__(
        self,
        added_columns: list[dict[str, Any]],
        removed_columns: list[str],
        type_changes: list[dict[str, Any]],
    ):
        self.added_columns = added_columns
        self.removed_columns = removed_columns
        self.type_changes = type_changes

    @property
    def has_changes(self) -> bool:
        return bool(self.added_columns or self.removed_columns or self.type_changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_columns": self.added_columns,
            "removed_columns": self.removed_columns,
            "type_changes": self.type_changes,
        }


class SchemaEngine:
    """Captures schema snapshots and detects drift."""

    @staticmethod
    def diff_schemas(
        old_columns: list[dict[str, Any]], new_columns: list[dict[str, Any]]
    ) -> SchemaDiff:
        """Compare two schema column lists and return differences."""
        old_by_name = {col["name"]: col for col in old_columns}
        new_by_name = {col["name"]: col for col in new_columns}

        old_names = set(old_by_name.keys())
        new_names = set(new_by_name.keys())

        added = [new_by_name[name] for name in sorted(new_names - old_names)]
        removed = sorted(old_names - new_names)

        type_changes = []
        for name in sorted(old_names & new_names):
            old_type = old_by_name[name].get("type", "")
            new_type = new_by_name[name].get("type", "")
            if old_type != new_type:
                type_changes.append({
                    "column": name,
                    "old_type": old_type,
                    "new_type": new_type,
                })

        return SchemaDiff(added_columns=added, removed_columns=removed, type_changes=type_changes)

    @staticmethod
    async def capture_snapshot(
        db: AsyncSession,
        connector: WarehouseConnector,
        table: MonitoredTable,
    ) -> SchemaSnapshot:
        """Fetch the current schema from the warehouse and store a snapshot."""
        full_table_name = f"{table.schema_name}.{table.table_name}"
        columns = await connector.get_schema(full_table_name)

        snapshot = SchemaSnapshot(
            table_id=table.id,
            columns_json=columns,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot

    @staticmethod
    async def detect_drift(
        db: AsyncSession,
        connector: WarehouseConnector,
        table: MonitoredTable,
    ) -> Alert | None:
        """Compare current schema against last snapshot and create an alert if changed."""
        # Get latest snapshot
        result = await db.execute(
            select(SchemaSnapshot)
            .where(SchemaSnapshot.table_id == table.id)
            .order_by(SchemaSnapshot.captured_at.desc())
            .limit(1)
        )
        previous_snapshot = result.scalar_one_or_none()

        # Capture new snapshot
        new_snapshot = await SchemaEngine.capture_snapshot(db, connector, table)

        if not previous_snapshot:
            # First snapshot — no drift to detect
            return None

        diff = SchemaEngine.diff_schemas(previous_snapshot.columns_json, new_snapshot.columns_json)

        if not diff.has_changes:
            return None

        # Create alert
        alert = Alert(
            table_id=table.id,
            type="schema_drift",
            severity="warning",
            status="open",
            details_json={
                "diff": diff.to_dict(),
                "previous_snapshot_id": str(previous_snapshot.id),
                "new_snapshot_id": str(new_snapshot.id),
            },
        )
        db.add(alert)
        await db.flush()
        return alert
