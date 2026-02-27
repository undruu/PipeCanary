from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.notifications.email import EmailNotifier, _render_alert_html, _wrap_html


@pytest.fixture
def notifier():
    return EmailNotifier(to_email="ops@example.com")


@pytest.fixture
def schema_drift_alert():
    return {
        "type": "schema_drift",
        "table_name": "public.users",
        "severity": "warning",
        "details": {"added_columns": "email", "removed_columns": "name"},
    }


@pytest.fixture
def row_count_alert():
    return {
        "type": "row_count",
        "table_name": "public.orders",
        "severity": "critical",
        "details": {"z_score": 4.5, "current_value": 200, "baseline_mean": 1000},
    }


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


class TestRenderAlertHtml:
    def test_contains_type_label(self, schema_drift_alert):
        html = _render_alert_html(schema_drift_alert)
        assert "Schema Drift" in html

    def test_contains_table_name(self, schema_drift_alert):
        html = _render_alert_html(schema_drift_alert)
        assert "public.users" in html

    def test_contains_severity(self, schema_drift_alert):
        html = _render_alert_html(schema_drift_alert)
        assert "warning" in html.lower()

    def test_critical_color(self, row_count_alert):
        html = _render_alert_html(row_count_alert)
        assert "#DC2626" in html

    def test_warning_color(self, schema_drift_alert):
        html = _render_alert_html(schema_drift_alert)
        assert "#F59E0B" in html

    def test_info_color(self):
        alert = {"type": "row_count", "table_name": "t", "severity": "info", "details": {}}
        html = _render_alert_html(alert)
        assert "#3B82F6" in html

    def test_details_rendered(self, schema_drift_alert):
        html = _render_alert_html(schema_drift_alert)
        assert "added_columns" in html
        assert "removed_columns" in html

    def test_no_details_no_table(self):
        alert = {"type": "row_count", "table_name": "t", "severity": "warning", "details": {}}
        html = _render_alert_html(alert)
        assert "<table" not in html

    def test_unknown_type_uses_raw_string(self):
        alert = {"type": "custom_check", "table_name": "t", "severity": "warning", "details": {}}
        html = _render_alert_html(alert)
        assert "custom_check" in html


class TestWrapHtml:
    def test_contains_subject(self):
        html = _wrap_html("<p>body</p>", subject="Test Subject")
        assert "Test Subject" in html

    def test_contains_pipecanary_branding(self):
        html = _wrap_html("<p>body</p>", subject="Test")
        assert "PipeCanary" in html

    def test_contains_body(self):
        html = _wrap_html("<p>Hello World</p>", subject="Test")
        assert "<p>Hello World</p>" in html


# ---------------------------------------------------------------------------
# send_alert
# ---------------------------------------------------------------------------


class TestSendAlert:
    async def test_success(self, notifier, schema_drift_alert):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with (
            patch("app.notifications.email.settings") as mock_settings,
            patch("app.notifications.email.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.sendgrid_api_key = "SG.fake-key"
            mock_settings.sendgrid_from_email = "alerts@pipecanary.io"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await notifier.send_alert(schema_drift_alert)
            assert result is True
            mock_client.post.assert_called_once()

            # Verify SendGrid API URL and auth header
            call_args = mock_client.post.call_args
            assert "sendgrid.com" in call_args[0][0]
            assert "Bearer SG.fake-key" in call_args[1]["headers"]["Authorization"]

    async def test_missing_api_key_returns_false(self, notifier, schema_drift_alert):
        with patch("app.notifications.email.settings") as mock_settings:
            mock_settings.sendgrid_api_key = ""
            result = await notifier.send_alert(schema_drift_alert)
            assert result is False

    async def test_empty_recipient_returns_false(self, schema_drift_alert):
        notifier = EmailNotifier(to_email="")
        with patch("app.notifications.email.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.fake-key"
            result = await notifier.send_alert(schema_drift_alert)
            assert result is False

    async def test_http_error_returns_false(self, notifier, schema_drift_alert):
        with (
            patch("app.notifications.email.settings") as mock_settings,
            patch("app.notifications.email.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.sendgrid_api_key = "SG.fake-key"
            mock_settings.sendgrid_from_email = "alerts@pipecanary.io"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Server error"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await notifier.send_alert(schema_drift_alert)
            assert result is False

    async def test_subject_contains_severity_and_table(self, notifier, schema_drift_alert):
        """Verify the subject line includes severity and table name."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with (
            patch("app.notifications.email.settings") as mock_settings,
            patch("app.notifications.email.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.sendgrid_api_key = "SG.fake-key"
            mock_settings.sendgrid_from_email = "alerts@pipecanary.io"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await notifier.send_alert(schema_drift_alert)

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            subject = payload["subject"]
            assert "WARNING" in subject
            assert "public.users" in subject


# ---------------------------------------------------------------------------
# send_digest
# ---------------------------------------------------------------------------


class TestSendDigest:
    async def test_digest_success(self, notifier, schema_drift_alert, row_count_alert):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with (
            patch("app.notifications.email.settings") as mock_settings,
            patch("app.notifications.email.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.sendgrid_api_key = "SG.fake-key"
            mock_settings.sendgrid_from_email = "alerts@pipecanary.io"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await notifier.send_digest([schema_drift_alert, row_count_alert])
            assert result is True

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert "2 alerts" in payload["subject"]
            html = payload["content"][0]["value"]
            assert "Schema Drift" in html
            assert "Row Count" in html

    async def test_digest_single_alert_no_plural(self, notifier, schema_drift_alert):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with (
            patch("app.notifications.email.settings") as mock_settings,
            patch("app.notifications.email.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.sendgrid_api_key = "SG.fake-key"
            mock_settings.sendgrid_from_email = "alerts@pipecanary.io"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await notifier.send_digest([schema_drift_alert])
            assert result is True

            call_args = mock_client.post.call_args
            payload = call_args[1]["json"]
            assert "1 alert " in payload["subject"]

    async def test_digest_empty_list_returns_false(self, notifier):
        with patch("app.notifications.email.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.fake-key"
            result = await notifier.send_digest([])
            assert result is False

    async def test_digest_missing_api_key_returns_false(self, notifier, schema_drift_alert):
        with patch("app.notifications.email.settings") as mock_settings:
            mock_settings.sendgrid_api_key = ""
            result = await notifier.send_digest([schema_drift_alert])
            assert result is False

    async def test_digest_http_error_returns_false(self, notifier, schema_drift_alert):
        with (
            patch("app.notifications.email.settings") as mock_settings,
            patch("app.notifications.email.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_settings.sendgrid_api_key = "SG.fake-key"
            mock_settings.sendgrid_from_email = "alerts@pipecanary.io"

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.HTTPError("Server error"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await notifier.send_digest([schema_drift_alert])
            assert result is False
