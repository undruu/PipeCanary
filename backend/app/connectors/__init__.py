from app.connectors.base import WarehouseConnector

__all__ = ["WarehouseConnector"]


def get_snowflake_connector(**kwargs):
    """Lazy factory to avoid importing snowflake SDK at module level."""
    from app.connectors.snowflake import SnowflakeConnector

    return SnowflakeConnector(**kwargs)
