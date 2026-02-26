from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.notifications.slack import SlackNotifier


@pytest.fixture
def notifier():
    return SlackNotifier(webhook_url="https://hooks.slack.com/services/T00/B00/xxxx")


@pytest.fixture
def schema_drift_alert():
    return {
        "type": "schema_drift",
        "table_name": "public.users",
        "severity": "warning",
        "details": {"added_columns": "email", "removed_columns": "name"},
    }


class TestFormatAlertMessage:
    def test_has_blocks_structure(self, notifier, schema_drift_alert):
        message = notifier._format_alert_message(schema_drift_alert)
        assert "blocks" in message
        assert isinstance(message["blocks"], list)
        assert len(message["blocks"]) >= 2

    def test_header_block(self, notifier, schema_drift_alert):
        message = notifier._format_alert_message(schema_drift_alert)
        header = message["blocks"][0]
        assert header["type"] == "header"
        assert "PipeCanary Alert" in header["text"]["text"]

    def test_schema_drift_type_label(self, notifier, schema_drift_alert):
        message = notifier._format_alert_message(schema_drift_alert)
        fields_text = " ".join(f["text"] for f in message["blocks"][1]["fields"])
        assert "Schema Drift" in fields_text

    def test_row_count_type_label(self, notifier):
        alert = {"type": "row_count", "table_name": "orders", "severity": "warning", "details": {}}
        message = notifier._format_alert_message(alert)
        fields_text = " ".join(f["text"] for f in message["blocks"][1]["fields"])
        assert "Row Count" in fields_text

    def test_null_rate_type_label(self, notifier):
        alert = {"type": "null_rate", "table_name": "orders", "severity": "info", "details": {}}
        message = notifier._format_alert_message(alert)
        fields_text = " ".join(f["text"] for f in message["blocks"][1]["fields"])
        assert "Null Rate" in fields_text

    def test_cardinality_type_label(self, notifier):
        alert = {"type": "cardinality", "table_name": "t", "severity": "warning", "details": {}}
        message = notifier._format_alert_message(alert)
        fields_text = " ".join(f["text"] for f in message["blocks"][1]["fields"])
        assert "Cardinality" in fields_text

    def test_unknown_type_uses_raw_string(self, notifier):
        alert = {"type": "custom_check", "table_name": "t", "severity": "warning", "details": {}}
        message = notifier._format_alert_message(alert)
        fields_text = " ".join(f["text"] for f in message["blocks"][1]["fields"])
        assert "custom_check" in fields_text

    def test_table_name_in_fields(self, notifier, schema_drift_alert):
        message = notifier._format_alert_message(schema_drift_alert)
        fields_text = " ".join(f["text"] for f in message["blocks"][1]["fields"])
        assert "public.users" in fields_text

    def test_critical_severity_emoji(self, notifier):
        alert = {"type": "row_count", "table_name": "t", "severity": "critical", "details": {}}
        message = notifier._format_alert_message(alert)
        assert ":red_circle:" in message["blocks"][0]["text"]["text"]

    def test_warning_severity_emoji(self, notifier):
        alert = {"type": "row_count", "table_name": "t", "severity": "warning", "details": {}}
        message = notifier._format_alert_message(alert)
        assert ":warning:" in message["blocks"][0]["text"]["text"]

    def test_info_severity_emoji(self, notifier):
        alert = {"type": "row_count", "table_name": "t", "severity": "info", "details": {}}
        message = notifier._format_alert_message(alert)
        assert ":information_source:" in message["blocks"][0]["text"]["text"]

    def test_unknown_severity_defaults_to_warning_emoji(self, notifier):
        alert = {"type": "row_count", "table_name": "t", "severity": "custom", "details": {}}
        message = notifier._format_alert_message(alert)
        assert ":warning:" in message["blocks"][0]["text"]["text"]

    def test_details_block_included_when_present(self, notifier, schema_drift_alert):
        message = notifier._format_alert_message(schema_drift_alert)
        # header + section + details = 3 blocks
        assert len(message["blocks"]) == 3
        detail_block = message["blocks"][2]
        assert "Details" in detail_block["text"]["text"]

    def test_no_details_block_when_empty(self, notifier):
        alert = {"type": "row_count", "table_name": "t", "severity": "warning", "details": {}}
        message = notifier._format_alert_message(alert)
        # header + section = 2 blocks (no details)
        assert len(message["blocks"]) == 2

    def test_details_formatted_as_bullet_list(self, notifier):
        alert = {
            "type": "row_count",
            "table_name": "t",
            "severity": "warning",
            "details": {"z_score": 4.5, "current_value": 200},
        }
        message = notifier._format_alert_message(alert)
        detail_text = message["blocks"][2]["text"]["text"]
        assert "z_score" in detail_text
        assert "current_value" in detail_text


class TestSendAlert:
    async def test_success(self, notifier, schema_drift_alert):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("app.notifications.slack.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await notifier.send_alert(schema_drift_alert)
            assert result is True
            mock_client.post.assert_called_once()
            # Verify the webhook URL and payload
            call_args = mock_client.post.call_args
            assert call_args[0][0] == notifier.webhook_url
            assert "blocks" in call_args[1]["json"]

    async def test_empty_webhook_url_returns_false(self, schema_drift_alert):
        notifier = SlackNotifier(webhook_url="")
        result = await notifier.send_alert(schema_drift_alert)
        assert result is False

    async def test_http_error_returns_false(self, notifier, schema_drift_alert):
        with patch("app.notifications.slack.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Server error"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await notifier.send_alert(schema_drift_alert)
            assert result is False
