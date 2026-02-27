from unittest.mock import MagicMock, patch

import pytest

from app.connectors.bigquery import BigQueryConnector


@pytest.fixture
def connector():
    return BigQueryConnector(
        project="test-project",
        credentials_info={"type": "service_account", "project_id": "test-project"},
        location="US",
    )


@pytest.fixture
def connector_with_path():
    return BigQueryConnector(
        project="test-project",
        credentials_path="/path/to/credentials.json",
    )


@pytest.fixture
def connector_default_creds():
    return BigQueryConnector(project="test-project")


class TestInit:
    def test_minimal_params(self):
        conn = BigQueryConnector(project="my-project")
        assert conn.project == "my-project"
        assert conn.credentials_info is None
        assert conn.credentials_path is None
        assert conn.location is None

    def test_full_params(self, connector):
        assert connector.project == "test-project"
        assert connector.credentials_info == {"type": "service_account", "project_id": "test-project"}
        assert connector.location == "US"

    def test_credentials_path(self, connector_with_path):
        assert connector_with_path.credentials_path == "/path/to/credentials.json"
        assert connector_with_path.credentials_info is None


class TestGetClient:
    @patch("app.connectors.bigquery.bigquery.Client")
    @patch("app.connectors.bigquery.service_account.Credentials.from_service_account_info")
    def test_with_credentials_info(self, mock_from_info, mock_client_cls, connector):
        mock_creds = MagicMock()
        mock_from_info.return_value = mock_creds

        connector._get_client()

        mock_from_info.assert_called_once_with(connector.credentials_info)
        mock_client_cls.assert_called_once_with(
            project="test-project", credentials=mock_creds, location="US"
        )

    @patch("app.connectors.bigquery.bigquery.Client")
    @patch("app.connectors.bigquery.service_account.Credentials.from_service_account_file")
    def test_with_credentials_path(self, mock_from_file, mock_client_cls, connector_with_path):
        mock_creds = MagicMock()
        mock_from_file.return_value = mock_creds

        connector_with_path._get_client()

        mock_from_file.assert_called_once_with("/path/to/credentials.json")
        mock_client_cls.assert_called_once_with(
            project="test-project", credentials=mock_creds
        )

    @patch("app.connectors.bigquery.bigquery.Client")
    def test_with_default_credentials(self, mock_client_cls, connector_default_creds):
        connector_default_creds._get_client()

        mock_client_cls.assert_called_once_with(
            project="test-project", credentials=None
        )


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
                ("users", "BASE TABLE", 1000),
                ("orders", "BASE TABLE", 5000),
            ]
            tables = await connector.get_tables("my_dataset")
            assert len(tables) == 2
            assert tables[0] == {
                "table_name": "users",
                "table_type": "BASE TABLE",
                "row_count": 1000,
            }
            assert tables[1] == {
                "table_name": "orders",
                "table_type": "BASE TABLE",
                "row_count": 5000,
            }
            # Verify the query uses the correct project/dataset path
            call_args = mock_exec.call_args[0][0]
            assert "test-project.my_dataset.INFORMATION_SCHEMA.TABLES" in call_args

    async def test_empty_dataset(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = []
            tables = await connector.get_tables("empty_dataset")
            assert tables == []


class TestGetSchema:
    async def test_dataset_dot_table_format(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [
                ("id", "INT64", "NO"),
                ("email", "STRING", "YES"),
            ]
            schema = await connector.get_schema("my_dataset.users")
            assert len(schema) == 2
            assert schema[0] == {"name": "id", "type": "INT64", "nullable": False}
            assert schema[1] == {"name": "email", "type": "STRING", "nullable": True}
            # Verify the query targets the correct INFORMATION_SCHEMA
            call_args = mock_exec.call_args[0][0]
            assert "test-project.my_dataset.INFORMATION_SCHEMA.COLUMNS" in call_args

    async def test_table_only_raises_error(self, connector):
        with pytest.raises(ValueError, match="BigQuery requires dataset-qualified table names"):
            await connector.get_schema("users")

    async def test_nullable_yes_maps_to_true(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [("name", "STRING", "YES")]
            schema = await connector.get_schema("my_dataset.users")
            assert schema[0]["nullable"] is True

    async def test_nullable_no_maps_to_false(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [("id", "INT64", "NO")]
            schema = await connector.get_schema("my_dataset.users")
            assert schema[0]["nullable"] is False


class TestGetRowCount:
    async def test_returns_count(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(42000,)]
            count = await connector.get_row_count("my_dataset.users")
            assert count == 42000
            call_args = mock_exec.call_args[0][0]
            assert "test-project.my_dataset.users" in call_args

    async def test_zero_rows(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(0,)]
            count = await connector.get_row_count("my_dataset.empty_table")
            assert count == 0


class TestGetNullCounts:
    async def test_returns_per_column_counts(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(5, 10)]
            result = await connector.get_null_counts("my_dataset.users", ["name", "email"])
            assert result == {"name": 5, "email": 10}

    async def test_single_column(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(42,)]
            result = await connector.get_null_counts("my_dataset.users", ["name"])
            assert result == {"name": 42}

    async def test_empty_result(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = []
            result = await connector.get_null_counts("my_dataset.users", ["name"])
            assert result == {"name": 0}

    async def test_query_uses_backtick_quoting(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(0,)]
            await connector.get_null_counts("my_dataset.users", ["name"])
            call_args = mock_exec.call_args[0][0]
            assert "`name`" in call_args


class TestGetCardinality:
    async def test_returns_distinct_counts(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(100, 50)]
            result = await connector.get_cardinality("my_dataset.users", ["name", "email"])
            assert result == {"name": 100, "email": 50}

    async def test_single_column(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(250,)]
            result = await connector.get_cardinality("my_dataset.users", ["status"])
            assert result == {"status": 250}

    async def test_empty_result(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = []
            result = await connector.get_cardinality("my_dataset.users", ["name"])
            assert result == {"name": 0}

    async def test_query_uses_backtick_quoting(self, connector):
        with patch.object(connector, "_execute") as mock_exec:
            mock_exec.return_value = [(0,)]
            await connector.get_cardinality("my_dataset.users", ["name"])
            call_args = mock_exec.call_args[0][0]
            assert "`name`" in call_args


class TestConnectorFactory:
    def test_factory_creates_bigquery_connector(self):
        from app.connectors import get_connector_for_connection

        connection = MagicMock()
        connection.type = "bigquery"
        connection.config = {
            "project": "my-project",
            "credentials_info": {"type": "service_account"},
            "location": "US",
        }

        connector = get_connector_for_connection(connection)
        assert isinstance(connector, BigQueryConnector)
        assert connector.project == "my-project"
        assert connector.credentials_info == {"type": "service_account"}
        assert connector.location == "US"

    def test_factory_with_credentials_path(self):
        from app.connectors import get_connector_for_connection

        connection = MagicMock()
        connection.type = "bigquery"
        connection.config = {
            "project": "my-project",
            "credentials_path": "/path/to/creds.json",
        }

        connector = get_connector_for_connection(connection)
        assert isinstance(connector, BigQueryConnector)
        assert connector.credentials_path == "/path/to/creds.json"

    def test_factory_with_minimal_config(self):
        from app.connectors import get_connector_for_connection

        connection = MagicMock()
        connection.type = "bigquery"
        connection.config = {"project": "my-project"}

        connector = get_connector_for_connection(connection)
        assert isinstance(connector, BigQueryConnector)
        assert connector.project == "my-project"
        assert connector.credentials_info is None
        assert connector.credentials_path is None
        assert connector.location is None
