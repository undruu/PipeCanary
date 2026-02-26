import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.deps import get_current_user
from app.database import get_db
from app.main import app


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


# ---------------------------------------------------------------------------
# Fake model dataclasses for API integration tests
# ---------------------------------------------------------------------------


@dataclass
class FakeUser:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: str = "test@example.com"
    name: str = "Test User"
    plan_tier: str = "free"
    password_hash: str | None = None
    auth_provider_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FakeOrganization:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = "Test Org"
    owner_id: uuid.UUID = field(default_factory=uuid.uuid4)
    plan_tier: str = "free"
    stripe_customer_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FakeConnection:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    org_id: uuid.UUID = field(default_factory=uuid.uuid4)
    type: str = "snowflake"
    name: str = "test-connection"
    credentials_ref: str = "local://test"
    config: dict | None = field(
        default_factory=lambda: {"account": "test", "user": "test", "password": "test"}
    )
    status: str = "pending"
    last_tested_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FakeAlert:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    table_id: uuid.UUID = field(default_factory=uuid.uuid4)
    type: str = "schema_drift"
    severity: str = "warning"
    status: str = "open"
    details_json: dict = field(default_factory=lambda: {"diff": {}})
    acknowledged_by: uuid.UUID | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_user():
    return FakeUser()


@pytest.fixture
def fake_org(fake_user):
    return FakeOrganization(owner_id=fake_user.id)


@pytest.fixture
def fake_connection(fake_org):
    return FakeConnection(org_id=fake_org.id)


@pytest.fixture
def fake_alert():
    return FakeAlert()


@pytest.fixture
def mock_db():
    """Mock async database session with fake refresh that populates server defaults."""
    db = AsyncMock()
    db.add = MagicMock()

    async def fake_refresh(instance, attribute_names=None, with_for_update=None):
        now = datetime.now(timezone.utc)
        # Populate primary key if not set (mimics DB-generated default)
        if hasattr(instance, "id") and getattr(instance, "id") is None:
            setattr(instance, "id", uuid.uuid4())
        for attr in ("created_at", "updated_at", "captured_at"):
            if hasattr(instance, attr) and getattr(instance, attr) is None:
                setattr(instance, attr, now)

    db.refresh = AsyncMock(side_effect=fake_refresh)
    return db


@pytest.fixture
def override_deps(fake_user, mock_db):
    """Override FastAPI dependencies with test doubles."""
    app.dependency_overrides[get_current_user] = lambda: fake_user

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
