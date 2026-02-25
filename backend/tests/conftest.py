import pytest


@pytest.fixture
def sample_schema_old():
    """Sample old schema for testing drift detection."""
    return [
        {"name": "id", "type": "NUMBER", "nullable": False},
        {"name": "email", "type": "VARCHAR", "nullable": False},
        {"name": "name", "type": "VARCHAR", "nullable": True},
        {"name": "created_at", "type": "TIMESTAMP_NTZ", "nullable": True},
    ]


@pytest.fixture
def sample_schema_new():
    """Sample new schema with changes for testing drift detection."""
    return [
        {"name": "id", "type": "NUMBER", "nullable": False},
        {"name": "email", "type": "VARCHAR", "nullable": False},
        {"name": "full_name", "type": "VARCHAR", "nullable": True},  # renamed from 'name'
        {"name": "created_at", "type": "TIMESTAMP_LTZ", "nullable": True},  # type changed
        {"name": "updated_at", "type": "TIMESTAMP_NTZ", "nullable": True},  # new column
    ]
