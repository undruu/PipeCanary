import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"

# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------

_SEVERITY_COLORS = {
    "critical": "#DC2626",
    "warning": "#F59E0B",
    "info": "#3B82F6",
}

_TYPE_LABELS = {
    "schema_drift": "Schema Drift",
    "row_count": "Row Count Anomaly",
    "null_rate": "Null Rate Spike",
    "cardinality": "Cardinality Shift",
}


def _render_alert_html(alert_data: dict[str, Any]) -> str:
    """Render a single alert into an HTML block."""
    alert_type = alert_data.get("type", "unknown")
    table_name = alert_data.get("table_name", "unknown")
    severity = alert_data.get("severity", "warning")
    details = alert_data.get("details", {})

    color = _SEVERITY_COLORS.get(severity, "#F59E0B")
    type_label = _TYPE_LABELS.get(alert_type, alert_type)

    detail_rows = ""
    if details:
        detail_rows = "".join(
            f"<tr><td style='padding:4px 8px;color:#6B7280;'>{k}</td>"
            f"<td style='padding:4px 8px;'>{v}</td></tr>"
            for k, v in details.items()
        )
        detail_rows = (
            "<table style='width:100%;border-collapse:collapse;margin-top:12px;'>"
            f"{detail_rows}</table>"
        )

    return f"""
    <div style="border-left:4px solid {color};padding:16px;margin-bottom:16px;
                background:#FAFAFA;border-radius:4px;">
      <div style="font-size:14px;font-weight:600;color:{color};
                  text-transform:uppercase;margin-bottom:4px;">
        {severity}
      </div>
      <div style="font-size:18px;font-weight:700;margin-bottom:8px;">
        {type_label}
      </div>
      <div style="font-size:14px;color:#374151;">
        Table: <code style="background:#E5E7EB;padding:2px 6px;border-radius:3px;">
          {table_name}</code>
      </div>
      {detail_rows}
    </div>"""


def _wrap_html(body: str, *, subject: str) -> str:
    """Wrap alert HTML blocks in a full email template."""
    year = datetime.now(timezone.utc).year
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{subject}</title></head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:-apple-system,BlinkMacSystemFont,
'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <div style="max-width:600px;margin:32px auto;background:#FFFFFF;border-radius:8px;
              overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    <!-- Header -->
    <div style="background:#1E293B;padding:24px 32px;">
      <h1 style="margin:0;color:#FFFFFF;font-size:20px;font-weight:700;">
        PipeCanary Alert
      </h1>
    </div>
    <!-- Body -->
    <div style="padding:24px 32px;">
      {body}
    </div>
    <!-- Footer -->
    <div style="padding:16px 32px;background:#F9FAFB;border-top:1px solid #E5E7EB;
                font-size:12px;color:#9CA3AF;text-align:center;">
      &copy; {year} PipeCanary &mdash; Data pipeline monitoring
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# EmailNotifier
# ---------------------------------------------------------------------------


class EmailNotifier:
    """Send formatted alert emails via the SendGrid v3 API."""

    def __init__(self, to_email: str):
        self.to_email = to_email

    # -- single alert -------------------------------------------------------

    async def send_alert(self, alert_data: dict[str, Any]) -> bool:
        """Send a single alert notification email.

        Returns True if the message was accepted by SendGrid.
        """
        if not settings.sendgrid_api_key:
            logger.warning("SendGrid API key not configured, skipping email notification")
            return False

        if not self.to_email:
            logger.warning("Recipient email not configured, skipping email notification")
            return False

        alert_type = alert_data.get("type", "alert")
        table_name = alert_data.get("table_name", "unknown")
        severity = alert_data.get("severity", "warning")
        type_label = _TYPE_LABELS.get(alert_type, alert_type)

        subject = f"[{severity.upper()}] {type_label} — {table_name}"
        body_html = _render_alert_html(alert_data)
        html_content = _wrap_html(body_html, subject=subject)

        return await self._send(subject=subject, html_content=html_content)

    # -- digest (batch) -----------------------------------------------------

    async def send_digest(self, alerts: list[dict[str, Any]]) -> bool:
        """Send a digest email containing multiple alerts.

        Returns True if the message was accepted by SendGrid.
        """
        if not settings.sendgrid_api_key:
            logger.warning("SendGrid API key not configured, skipping email digest")
            return False

        if not self.to_email:
            logger.warning("Recipient email not configured, skipping email digest")
            return False

        if not alerts:
            return False

        count = len(alerts)
        subject = f"[PipeCanary Digest] {count} alert{'s' if count != 1 else ''} detected"

        summary = (
            f"<p style='font-size:14px;color:#374151;margin-bottom:16px;'>"
            f"PipeCanary detected <strong>{count}</strong> "
            f"alert{'s' if count != 1 else ''} during the latest check run.</p>"
        )

        alert_blocks = "".join(_render_alert_html(a) for a in alerts)
        html_content = _wrap_html(summary + alert_blocks, subject=subject)

        return await self._send(subject=subject, html_content=html_content)

    # -- internal -----------------------------------------------------------

    async def _send(self, *, subject: str, html_content: str) -> bool:
        """Post an email via the SendGrid v3 Mail Send API."""
        payload = {
            "personalizations": [{"to": [{"email": self.to_email}]}],
            "from": {"email": settings.sendgrid_from_email, "name": "PipeCanary"},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_content}],
        }
        headers = {
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    SENDGRID_API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError:
            logger.exception("Failed to send email notification to %s", self.to_email)
            return False
