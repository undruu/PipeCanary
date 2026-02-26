import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

API_PREFIX = "/api/v1"


class TestCreateConnection:
    async def test_create_success(self, override_deps, mock_db, fake_org):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_org
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"{API_PREFIX}/connections",
                json={
                    "type": "snowflake",
                    "name": "my-warehouse",
                    "credentials": {"account": "acct", "user": "usr", "password": "pwd"},
                    "config": {"warehouse": "COMPUTE_WH"},
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "snowflake"
        assert data["name"] == "my-warehouse"
        assert data["status"] == "pending"
        assert data["config"]["account"] == "acct"
        assert data["config"]["warehouse"] == "COMPUTE_WH"

    async def test_create_no_organization(self, override_deps, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"{API_PREFIX}/connections",
                json={
                    "type": "snowflake",
                    "name": "my-warehouse",
                    "credentials": {"account": "acct", "user": "usr"},
                },
            )

        assert response.status_code == 400
        assert "No organization" in response.json()["detail"]


class TestTestConnection:
    async def test_success(self, override_deps, mock_db, fake_connection):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_connection
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.connections.get_connector_for_connection") as mock_factory:
            mock_connector = AsyncMock()
            mock_connector.test_connection = AsyncMock(return_value=True)
            mock_factory.return_value = mock_connector

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"{API_PREFIX}/connections/{fake_connection.id}/test"
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successful" in data["message"]
        assert fake_connection.status == "active"

    async def test_connection_not_found(self, override_deps, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"{API_PREFIX}/connections/{uuid.uuid4()}/test"
            )

        assert response.status_code == 404

    async def test_failed_connection(self, override_deps, mock_db, fake_connection):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_connection
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.connections.get_connector_for_connection") as mock_factory:
            mock_connector = AsyncMock()
            mock_connector.test_connection = AsyncMock(return_value=False)
            mock_factory.return_value = mock_connector

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"{API_PREFIX}/connections/{fake_connection.id}/test"
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "failed" in data["message"]
        assert fake_connection.status == "failed"

    async def test_unsupported_connector_type(self, override_deps, mock_db, fake_connection):
        fake_connection.type = "unsupported_db"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_connection
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.connections.get_connector_for_connection") as mock_factory:
            mock_factory.side_effect = ValueError("Unsupported connection type: unsupported_db")

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"{API_PREFIX}/connections/{fake_connection.id}/test"
                )

        assert response.status_code == 400
        assert "Unsupported" in response.json()["detail"]


class TestListTables:
    async def test_success(self, override_deps, mock_db, fake_connection):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_connection
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_tables = [
            {"table_name": "USERS", "table_type": "BASE TABLE", "row_count": 1000},
            {"table_name": "ORDERS", "table_type": "BASE TABLE", "row_count": 5000},
        ]

        with patch("app.api.connections.get_connector_for_connection") as mock_factory:
            mock_connector = AsyncMock()
            mock_connector.get_tables = AsyncMock(return_value=mock_tables)
            mock_factory.return_value = mock_connector

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"{API_PREFIX}/connections/{fake_connection.id}/tables",
                    params={"schema": "PUBLIC"},
                )

        assert response.status_code == 200
        data = response.json()
        assert len(data["tables"]) == 2
        assert data["tables"][0]["table_name"] == "USERS"

    async def test_connection_not_found(self, override_deps, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"{API_PREFIX}/connections/{uuid.uuid4()}/tables",
                params={"schema": "PUBLIC"},
            )

        assert response.status_code == 404

    async def test_warehouse_error(self, override_deps, mock_db, fake_connection):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_connection
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.connections.get_connector_for_connection") as mock_factory:
            mock_connector = AsyncMock()
            mock_connector.get_tables = AsyncMock(
                side_effect=Exception("Warehouse unavailable")
            )
            mock_factory.return_value = mock_connector

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"{API_PREFIX}/connections/{fake_connection.id}/tables",
                    params={"schema": "PUBLIC"},
                )

        assert response.status_code == 502
        assert "Failed to retrieve" in response.json()["detail"]

    async def test_missing_schema_param(self, override_deps, mock_db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                f"{API_PREFIX}/connections/{uuid.uuid4()}/tables",
            )

        assert response.status_code == 422
