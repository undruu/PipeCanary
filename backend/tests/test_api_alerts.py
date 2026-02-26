import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from app.main import app

API_PREFIX = "/api/v1"


class TestListAlerts:
    async def test_list_all(self, override_deps, mock_db, fake_alert):
        @dataclass
        class _Alert:
            id: uuid.UUID = field(default_factory=uuid.uuid4)
            table_id: uuid.UUID = field(default_factory=uuid.uuid4)
            type: str = "row_count"
            severity: str = "critical"
            status: str = "open"
            details_json: dict = field(default_factory=dict)
            acknowledged_by: uuid.UUID | None = None
            acknowledged_at: datetime | None = None
            resolved_at: datetime | None = None
            created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

        alert2 = _Alert()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [fake_alert, alert2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"{API_PREFIX}/alerts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["type"] == "schema_drift"
        assert data[1]["type"] == "row_count"

    async def test_list_empty(self, override_deps, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"{API_PREFIX}/alerts")

        assert response.status_code == 200
        assert response.json() == []

    async def test_filter_by_status(self, override_deps, mock_db, fake_alert):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [fake_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"{API_PREFIX}/alerts", params={"status": "open"}
            )

        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_filter_by_alert_type(self, override_deps, mock_db, fake_alert):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [fake_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"{API_PREFIX}/alerts", params={"alert_type": "schema_drift"}
            )

        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_filter_by_table_id(self, override_deps, mock_db, fake_alert):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [fake_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"{API_PREFIX}/alerts", params={"table_id": str(fake_alert.table_id)}
            )

        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_pagination(self, override_deps, mock_db, fake_alert):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [fake_alert]
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"{API_PREFIX}/alerts", params={"limit": 10, "offset": 0}
            )

        assert response.status_code == 200


class TestUpdateAlert:
    async def test_acknowledge(self, override_deps, mock_db, fake_alert, fake_user):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_alert
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/alerts/{fake_alert.id}",
                json={"status": "acknowledged"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"
        assert data["acknowledged_by"] == str(fake_user.id)
        assert data["acknowledged_at"] is not None

    async def test_resolve(self, override_deps, mock_db, fake_alert):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_alert
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/alerts/{fake_alert.id}",
                json={"status": "resolved"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None

    async def test_snooze(self, override_deps, mock_db, fake_alert):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_alert
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/alerts/{fake_alert.id}",
                json={"status": "snoozed"},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "snoozed"

    async def test_not_found(self, override_deps, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/alerts/{uuid.uuid4()}",
                json={"status": "acknowledged"},
            )

        assert response.status_code == 404

    async def test_invalid_status(self, override_deps, mock_db, fake_alert):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_alert
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                f"{API_PREFIX}/alerts/{fake_alert.id}",
                json={"status": "invalid_status"},
            )

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]
