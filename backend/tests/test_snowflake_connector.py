from unittest.mock import patch

import pytest

from app.connectors.snowflake import SnowflakeConnector


@pytest.fixture
def connector():
    return SnowflakeConnector(
        account="test_account",
        user="test_user",
        password="test_password",
        warehouse="test_warehouse",
        database="test_db",
        role="test_role",
    )


class TestGetConnectionParams:
    def test_minimal_params(self):
        conn = SnowflakeConnector(account="acct", user="usr")
        params = conn._get_connection_params()
        assert params == {"account": "acct", "user": "usr"}

    def test_full_params(self, connector):
        params = connector._get_connection_params()
        assert params["account"] == "test_account"
        assert params["user"] == "test_user"
        assert params["password"] == "test_password"
        assert params["warehouse"] == "test_warehouse"
        assert params["database"] == "test_db"
        assert params["role"] == "test_role"
        assert len(params) == 6

    def test_with_private_key(self):
        conn = SnowflakeConnector(
            account="acct", user="usr", private_key=b"key_data"
        )
        params = conn._get_connection_params()
        assert params["private_key"] == b"key_data"
        assert "password" not in params

    def test_password_and_key_both_set(self):
        conn = SnowflakeConnector(
            account="acct", user="usr", password="pwd", private_key=b"key"
        )
        params = conn._get_connection_params()
        assert params["password"] == "pwd"
        assert params["private_key"] == b"key"


class TestTestConnection:
    async def test_success(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(1,)]
            result = await connector.test_connection()
            assert result is True
            mock_exec.assert_called_once_with("SELECT 1")

    async def test_failure_on_exception(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.side_effect = Exception("Connection refused")
            result = await connector.test_connection()
            assert result is False

    async def test_failure_on_empty_result(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = []
            result = await connector.test_connection()
            assert result is False


class TestGetTables:
    async def test_returns_formatted_tables(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [
                ("USERS", "BASE TABLE", 1000),
                ("ORDERS", "BASE TABLE", 5000),
            ]
            tables = await connector.get_tables("PUBLIC")
            assert len(tables) == 2
            assert tables[0] == {
                "table_name": "USERS",
                "table_type": "BASE TABLE",
                "row_count": 1000,
            }
            assert tables[1] == {
                "table_name": "ORDERS",
                "table_type": "BASE TABLE",
                "row_count": 5000,
            }

    async def test_empty_schema(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = []
            tables = await connector.get_tables("EMPTY_SCHEMA")
            assert tables == []


class TestGetSchema:
    async def test_schema_dot_table_format(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [
                ("ID", "NUMBER", "NO"),
                ("EMAIL", "VARCHAR", "YES"),
            ]
            schema = await connector.get_schema("PUBLIC.USERS")
            assert len(schema) == 2
            assert schema[0] == {"name": "ID", "type": "NUMBER", "nullable": False}
            assert schema[1] == {"name": "EMAIL", "type": "VARCHAR", "nullable": True}

    async def test_table_only_format(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [("ID", "NUMBER", "NO")]
            schema = await connector.get_schema("USERS")
            assert len(schema) == 1
            assert schema[0]["name"] == "ID"
            assert schema[0]["nullable"] is False

    async def test_nullable_yes_maps_to_true(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [("NAME", "VARCHAR", "YES")]
            schema = await connector.get_schema("USERS")
            assert schema[0]["nullable"] is True


class TestGetRowCount:
    async def test_returns_count(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(42000,)]
            count = await connector.get_row_count("PUBLIC.USERS")
            assert count == 42000

    async def test_zero_rows(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(0,)]
            count = await connector.get_row_count("PUBLIC.EMPTY_TABLE")
            assert count == 0


class TestGetNullCounts:
    async def test_returns_per_column_counts(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(5, 10)]
            result = await connector.get_null_counts("PUBLIC.USERS", ["name", "email"])
            assert result == {"name": 5, "email": 10}

    async def test_single_column(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(42,)]
            result = await connector.get_null_counts("PUBLIC.USERS", ["name"])
            assert result == {"name": 42}

    async def test_empty_result(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = []
            result = await connector.get_null_counts("PUBLIC.USERS", ["name"])
            assert result == {"name": 0}


class TestGetCardinality:
    async def test_returns_distinct_counts(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(100, 50)]
            result = await connector.get_cardinality("PUBLIC.USERS", ["name", "email"])
            assert result == {"name": 100, "email": 50}

    async def test_single_column(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(250,)]
            result = await connector.get_cardinality("PUBLIC.USERS", ["status"])
            assert result == {"status": 250}

    async def test_empty_result(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = []
            result = await connector.get_cardinality("PUBLIC.USERS", ["name"])
            assert result == {"name": 0}
