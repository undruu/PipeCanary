from app.connectors.base import WarehouseConnector

__all__ = ["WarehouseConnector", "get_connector_for_connection"]

_CONNECTOR_TYPES = {"snowflake"}


def get_snowflake_connector(**kwargs):
    """Lazy factory to avoid importing snowflake SDK at module level."""
    from app.connectors.snowflake import SnowflakeConnector

    return SnowflakeConnector(**kwargs)


def get_connector_for_connection(connection) -> WarehouseConnector:
    """Build the appropriate WarehouseConnector from a Connection model.

    The connection's ``config`` JSONB column must contain the credential and
    connection parameters required by the target warehouse.  For Snowflake
    this means at least ``account``, ``user``, and either ``password`` or
    ``private_key``, plus optional ``warehouse``, ``database``, and ``role``.
    """
    config: dict = connection.config or {}
    connector_type: str = connection.type

    if connector_type == "snowflake":
        return get_snowflake_connector(
            account=config.get("account", ""),
            user=config.get("user", ""),
            password=config.get("password"),
            private_key=config.get("private_key"),
            warehouse=config.get("warehouse"),
            database=config.get("database"),
            role=config.get("role"),
        )

    raise ValueError(f"Unsupported connection type: {connector_type}")
