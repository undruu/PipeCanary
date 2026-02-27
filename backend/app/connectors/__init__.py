from app.connectors.base import WarehouseConnector

__all__ = ["WarehouseConnector", "get_connector_for_connection"]

_CONNECTOR_TYPES = {"snowflake", "bigquery"}


def get_snowflake_connector(**kwargs):
    """Lazy factory to avoid importing snowflake SDK at module level."""
    from app.connectors.snowflake import SnowflakeConnector

    return SnowflakeConnector(**kwargs)


def get_bigquery_connector(**kwargs):
    """Lazy factory to avoid importing BigQuery SDK at module level."""
    from app.connectors.bigquery import BigQueryConnector

    return BigQueryConnector(**kwargs)


def get_connector_for_connection(connection) -> WarehouseConnector:
    """Build the appropriate WarehouseConnector from a Connection model.

    The connection's ``config`` JSONB column must contain the credential and
    connection parameters required by the target warehouse.  For Snowflake
    this means at least ``account``, ``user``, and either ``password`` or
    ``private_key``, plus optional ``warehouse``, ``database``, and ``role``.
    For BigQuery this means ``project`` and either ``credentials_info`` (a
    service-account JSON dict) or ``credentials_path``.
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

    if connector_type == "bigquery":
        return get_bigquery_connector(
            project=config.get("project", ""),
            credentials_info=config.get("credentials_info"),
            credentials_path=config.get("credentials_path"),
            location=config.get("location"),
        )

    raise ValueError(f"Unsupported connection type: {connector_type}")
