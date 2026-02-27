import asyncio
from typing import Any

from google.cloud import bigquery
from google.oauth2 import service_account

from app.connectors.base import WarehouseConnector


class BigQueryConnector(WarehouseConnector):
    """BigQuery warehouse connector using service account authentication."""

    def __init__(
        self,
        project: str,
        credentials_info: dict | None = None,
        credentials_path: str | None = None,
        location: str | None = None,
    ):
        self.project = project
        self.credentials_info = credentials_info
        self.credentials_path = credentials_path
        self.location = location

    def _get_client(self) -> bigquery.Client:
        """Build a BigQuery client with the configured credentials."""
        if self.credentials_info:
            creds = service_account.Credentials.from_service_account_info(self.credentials_info)
        elif self.credentials_path:
            creds = service_account.Credentials.from_service_account_file(self.credentials_path)
        else:
            creds = None  # Falls back to Application Default Credentials

        kwargs: dict[str, Any] = {"project": self.project, "credentials": creds}
        if self.location:
            kwargs["location"] = self.location
        return bigquery.Client(**kwargs)

    def _query_sync(self, query: str, params: list | None = None) -> list[tuple]:
        """Execute a query synchronously against BigQuery."""
        client = self._get_client()
        try:
            job_config = None
            if params:
                job_config = bigquery.QueryJobConfig(query_parameters=params)
            result = client.query(query, job_config=job_config).result()
            return [tuple(row.values()) for row in result]
        finally:
            client.close()

    async def _execute(self, query: str, params: list | None = None) -> list[tuple]:
        """Execute a query in a thread pool to avoid blocking the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._query_sync, query, params)

    async def test_connection(self) -> bool:
        """Validate credentials by running a simple query."""
        try:
            result = await self._execute("SELECT 1")
            return len(result) > 0
        except Exception:
            return False

    async def get_tables(self, schema: str) -> list[dict[str, Any]]:
        """List available tables in a dataset (schema).

        Uses INFORMATION_SCHEMA.TABLES which requires the dataset to be
        specified in the FROM clause for BigQuery.
        """
        query = (
            f"SELECT table_name, table_type, "  # noqa: S608
            f"CAST(IFNULL(row_count, 0) AS INT64) AS row_count "
            f"FROM `{self.project}.{schema}.INFORMATION_SCHEMA.TABLES` "
            f"ORDER BY table_name"
        )
        rows = await self._execute(query)
        return [
            {"table_name": row[0], "table_type": row[1], "row_count": row[2]}
            for row in rows
        ]

    async def get_schema(self, table: str) -> list[dict[str, Any]]:
        """Return column names, types, and nullability for a table.

        Accepts ``dataset.table`` or just ``table`` format.
        """
        parts = table.split(".")
        if len(parts) == 2:
            dataset, table_name = parts
            query = (
                f"SELECT column_name, data_type, is_nullable "  # noqa: S608
                f"FROM `{self.project}.{dataset}.INFORMATION_SCHEMA.COLUMNS` "
                f"WHERE table_name = @table_name "
                f"ORDER BY ordinal_position"
            )
            params = [bigquery.ScalarQueryParameter("table_name", "STRING", table_name)]
        else:
            # Without a dataset qualifier we cannot target INFORMATION_SCHEMA;
            # the caller should always provide dataset.table for BigQuery.
            raise ValueError("BigQuery requires dataset-qualified table names (dataset.table)")

        rows = await self._execute(query, params)
        return [
            {"name": row[0], "type": row[1], "nullable": row[2] == "YES"}
            for row in rows
        ]

    async def get_row_count(self, table: str) -> int:
        """Return current row count for a table."""
        rows = await self._execute(f"SELECT COUNT(*) FROM `{self.project}.{table}`")  # noqa: S608
        return rows[0][0]

    async def get_null_counts(self, table: str, columns: list[str]) -> dict[str, int]:
        """Return null count per column."""
        expressions = [f"SUM(CASE WHEN `{col}` IS NULL THEN 1 ELSE 0 END)" for col in columns]
        query = f"SELECT {', '.join(expressions)} FROM `{self.project}.{table}`"  # noqa: S608
        rows = await self._execute(query)
        if not rows:
            return {col: 0 for col in columns}
        return {col: rows[0][i] for i, col in enumerate(columns)}

    async def get_cardinality(self, table: str, columns: list[str]) -> dict[str, int]:
        """Return distinct value count per column."""
        expressions = [f"COUNT(DISTINCT `{col}`)" for col in columns]
        query = f"SELECT {', '.join(expressions)} FROM `{self.project}.{table}`"  # noqa: S608
        rows = await self._execute(query)
        if not rows:
            return {col: 0 for col in columns}
        return {col: rows[0][i] for i, col in enumerate(columns)}
