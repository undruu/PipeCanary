import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.tasks.monitoring import FREQUENCY_INTERVALS, _is_table_due

API_PREFIX = "/api/v1"


# ---------------------------------------------------------------------------
# Fake MonitoredTable for both unit tests and API tests
# ---------------------------------------------------------------------------


@dataclass
class FakeMonitoredTable:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    connection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    schema_name: str = "public"
    table_name: str = "orders"
    check_frequency: str = "daily"
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Unit tests: _is_table_due
# ---------------------------------------------------------------------------


class TestIsTableDue:
    def test_never_checked_is_always_due(self):
        table = FakeMonitoredTable(check_frequency="daily")
        now = datetime.now(timezone.utc)
        assert _is_table_due(table, last_check_at=None, now=now) is True

    def test_hourly_due_after_one_hour(self):
        table = FakeMonitoredTable(check_frequency="hourly")
        now = datetime.now(timezone.utc)
        last_check = now - timedelta(hours=1, minutes=1)
        assert _is_table_due(table, last_check_at=last_check, now=now) is True

    def test_hourly_not_due_before_one_hour(self):
        table = FakeMonitoredTable(check_frequency="hourly")
        now = datetime.now(timezone.utc)
        last_check = now - timedelta(minutes=30)
        assert _is_table_due(table, last_check_at=last_check, now=now) is False

    def test_daily_due_after_24_hours(self):
        table = FakeMonitoredTable(check_frequency="daily")
        now = datetime.now(timezone.utc)
        last_check = now - timedelta(hours=25)
        assert _is_table_due(table, last_check_at=last_check, now=now) is True

    def test_daily_not_due_before_24_hours(self):
        table = FakeMonitoredTable(check_frequency="daily")
        now = datetime.now(timezone.utc)
        last_check = now - timedelta(hours=12)
        assert _is_table_due(table, last_check_at=last_check, now=now) is False

    def test_every_6h_due_after_6_hours(self):
        table = FakeMonitoredTable(check_frequency="every_6h")
        now = datetime.now(timezone.utc)
        last_check = now - timedelta(hours=6)
        assert _is_table_due(table, last_check_at=last_check, now=now) is True

    def test_every_12h_not_due_before_12_hours(self):
        table = FakeMonitoredTable(check_frequency="every_12h")
        now = datetime.now(timezone.utc)
        last_check = now - timedelta(hours=8)
        assert _is_table_due(table, last_check_at=last_check, now=now) is False

    def test_weekly_due_after_7_days(self):
        table = FakeMonitoredTable(check_frequency="weekly")
        now = datetime.now(timezone.utc)
        last_check = now - timedelta(days=7, hours=1)
        assert _is_table_due(table, last_check_at=last_check, now=now) is True

    def test_weekly_not_due_before_7_days(self):
        table = FakeMonitoredTable(check_frequency="weekly")
        now = datetime.now(timezone.utc)
        last_check = now - timedelta(days=5)
        assert _is_table_due(table, last_check_at=last_check, now=now) is False

    def test_unknown_frequency_defaults_to_daily(self):
        table = FakeMonitoredTable(check_frequency="unknown_value")
        now = datetime.now(timezone.utc)
        # 25 hours ago → should be due (defaults to daily = 24h)
        last_check = now - timedelta(hours=25)
        assert _is_table_due(table, last_check_at=last_check, now=now) is True

        # 12 hours ago → should not be due
        last_check = now - timedelta(hours=12)
        assert _is_table_due(table, last_check_at=last_check, now=now) is False

    def test_all_valid_frequencies_have_intervals(self):
        from app.schemas.table import VALID_FREQUENCIES

        for freq in VALID_FREQUENCIES:
            assert freq in FREQUENCY_INTERVALS, f"Missing interval for frequency: {freq}"


# ---------------------------------------------------------------------------
# API tests: GET /tables/{id}/schedule
# ---------------------------------------------------------------------------


class TestGetTableSchedule:
    async def test_success(self, override_deps, mock_db):
        table = FakeMonitoredTable()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = table
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"{API_PREFIX}/tables/{table.id}/schedule")

        assert response.status_code == 200
        data = response.json()
        assert data["check_frequency"] == "daily"
        assert data["is_active"] is True
        assert data["schema_name"] == "public"
        assert data["table_name"] == "orders"

    async def test_not_found(self, override_deps, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"{API_PREFIX}/tables/{uuid.uuid4()}/schedule")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# API tests: PATCH /tables/{id}/schedule
# ---------------------------------------------------------------------------


class TestUpdateTableSchedule:
    async def test_update_frequency(self, override_deps, mock_db):
        table = FakeMonitoredTable(check_frequency="daily")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = table
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/tables/{table.id}/schedule",
                json={"check_frequency": "hourly"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["check_frequency"] == "hourly"

    async def test_update_is_active(self, override_deps, mock_db):
        table = FakeMonitoredTable(is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = table
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/tables/{table.id}/schedule",
                json={"is_active": False},
            )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    async def test_update_both_fields(self, override_deps, mock_db):
        table = FakeMonitoredTable(check_frequency="daily", is_active=True)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = table
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/tables/{table.id}/schedule",
                json={"check_frequency": "weekly", "is_active": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["check_frequency"] == "weekly"
        assert data["is_active"] is False

    async def test_invalid_frequency_rejected(self, override_deps, mock_db):
        table = FakeMonitoredTable()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = table
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/tables/{table.id}/schedule",
                json={"check_frequency": "every_5_minutes"},
            )

        assert response.status_code == 400
        assert "Invalid frequency" in response.json()["detail"]

    async def test_not_found(self, override_deps, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/tables/{uuid.uuid4()}/schedule",
                json={"check_frequency": "hourly"},
            )

        assert response.status_code == 404

    async def test_all_valid_frequencies_accepted(self, override_deps, mock_db):
        """Every value in VALID_FREQUENCIES should be accepted by the endpoint."""
        from app.schemas.table import VALID_FREQUENCIES

        for freq in sorted(VALID_FREQUENCIES):
            table = FakeMonitoredTable()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = table
            mock_db.execute = AsyncMock(return_value=mock_result)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"{API_PREFIX}/tables/{table.id}/schedule",
                    json={"check_frequency": freq},
                )

            assert response.status_code == 200, f"Frequency '{freq}' was rejected"
            assert response.json()["check_frequency"] == freq
