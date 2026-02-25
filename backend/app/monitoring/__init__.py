__all__ = ["SchemaEngine"]


def __getattr__(name):
    if name == "SchemaEngine":
        from app.monitoring.schema_engine import SchemaEngine

        return SchemaEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
