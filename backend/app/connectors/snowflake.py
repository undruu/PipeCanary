import asyncio
from typing import Any

import snowflake.connector

from app.connectors.base import WarehouseConnector


class SnowflakeConnector(WarehouseConnector):
    """Snowflake warehouse connector using key-pair or password auth."""

    def __init__(
        self,
        account: str,
        user: str,
        password: str | None = None,
        private_key: bytes | None = None,
        warehouse: str | None = None,
        database: str | None = None,
        role: str | None = None,
    ):
        self.account = account
        self.user = user
        self.password = password
        self.private_key = private_key
        self.warehouse = warehouse
        self.database = database
        self.role = role

    def _get_connection_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "account": self.account,
            "user": self.user,
        }
        if self.password:
            params["password"] = self.password
        if self.private_key:
            params["private_key"] = self.private_key
        if self.warehouse:
            params["warehouse"] = self.warehouse
        if self.database:
            params["database"] = self.database
        if self.role:
            params["role"] = self.role
        return params

    def _execute_sync(self, query: str, params: dict | None = None) -> list[tuple]:
        """Execute a query synchronously against Snowflake."""
        conn = snowflake.connector.connect(**self._get_connection_params())
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            conn.close()

    async def _execute(self, query: str, params: dict | None = None) -> list[tuple]:
        """Execute a query in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, query, params)

    async def test_connection(self) -> bool:
        """Validate credentials by running a simple query."""
        try:
            result = await self._execute("SELECT 1")
            return len(result) > 0
        except Exception:
            return False

    async def get_tables(self, schema: str) -> list[dict[str, Any]]:
        """List available tables in a schema."""
        rows = await self._execute(
            "SELECT TABLE_NAME, TABLE_TYPE, ROW_COUNT "
            "FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME",
            {"1": schema.upper()},
        )
        return [
            {"table_name": row[0], "table_type": row[1], "row_count": row[2]}
            for row in rows
        ]

    async def get_schema(self, table: str) -> list[dict[str, Any]]:
        """Return column names, types, and nullability for a table."""
        parts = table.split(".")
        if len(parts) == 2:
            schema, table_name = parts
            query = (
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                "ORDER BY ORDINAL_POSITION"
            )
            rows = await self._execute(query, {"1": schema.upper(), "2": table_name.upper()})
        else:
            query = (
                "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME = %s "
                "ORDER BY ORDINAL_POSITION"
            )
            rows = await self._execute(query, {"1": table.upper()})

        return [
            {"name": row[0], "type": row[1], "nullable": row[2] == "YES"}
            for row in rows
        ]

    async def get_row_count(self, table: str) -> int:
        """Return current row count for a table."""
        rows = await self._execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
        return rows[0][0]

    async def get_null_counts(self, table: str, columns: list[str]) -> dict[str, int]:
        """Return null count per column."""
        expressions = [f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS {col}_nulls" for col in columns]
        query = f"SELECT {', '.join(expressions)} FROM {table}"  # noqa: S608
        rows = await self._execute(query)
        if not rows:
            return {col: 0 for col in columns}
        return {col: rows[0][i] for i, col in enumerate(columns)}

    async def get_cardinality(self, table: str, columns: list[str]) -> dict[str, int]:
        """Return distinct value count per column."""
        expressions = [f"COUNT(DISTINCT {col}) AS {col}_distinct" for col in columns]
        query = f"SELECT {', '.join(expressions)} FROM {table}"  # noqa: S608
        rows = await self._execute(query)
        if not rows:
            return {col: 0 for col in columns}
        return {col: rows[0][i] for i, col in enumerate(columns)}
