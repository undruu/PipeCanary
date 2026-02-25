from abc import ABC, abstractmethod
from typing import Any


class WarehouseConnector(ABC):
    """Base interface for all warehouse connectors."""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Validate credentials and connectivity."""
        ...

    @abstractmethod
    async def get_tables(self, schema: str) -> list[dict[str, Any]]:
        """List available tables in a schema."""
        ...

    @abstractmethod
    async def get_schema(self, table: str) -> list[dict[str, Any]]:
        """Return column names, types, and nullability."""
        ...

    @abstractmethod
    async def get_row_count(self, table: str) -> int:
        """Return current row count."""
        ...

    @abstractmethod
    async def get_null_counts(self, table: str, columns: list[str]) -> dict[str, int]:
        """Return null count per column."""
        ...

    @abstractmethod
    async def get_cardinality(self, table: str, columns: list[str]) -> dict[str, int]:
        """Return distinct value count per column."""
        ...
