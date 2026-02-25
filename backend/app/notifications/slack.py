import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send formatted alert messages to a Slack webhook."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _format_alert_message(self, alert_data: dict[str, Any]) -> dict:
        """Format an alert into a Slack Block Kit message."""
        alert_type = alert_data.get("type", "unknown")
        table_name = alert_data.get("table_name", "unknown")
        severity = alert_data.get("severity", "warning")
        details = alert_data.get("details", {})

        severity_emoji = {
            "critical": ":red_circle:",
            "warning": ":warning:",
            "info": ":information_source:",
        }.get(severity, ":warning:")

        type_label = {
            "schema_drift": ":duck: Schema Drift",
            "row_count": ":bird: Row Count Anomaly",
            "null_rate": ":seagull: Null Rate Spike",
            "cardinality": ":cardinal: Cardinality Shift",
        }.get(alert_type, alert_type)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} PipeCanary Alert",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Type:*\n{type_label}"},
                    {"type": "mrkdwn", "text": f"*Table:*\n`{table_name}`"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                ],
            },
        ]

        if details:
            detail_text = "\n".join(f"• {k}: {v}" for k, v in details.items())
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Details:*\n{detail_text}"},
            })

        return {"blocks": blocks}

    async def send_alert(self, alert_data: dict[str, Any]) -> bool:
        """Send an alert notification to Slack.

        Returns True if the message was sent successfully.
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured, skipping notification")
            return False

        message = self._format_alert_message(alert_data)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=message)
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            logger.exception("Failed to send Slack notification")
            return False
