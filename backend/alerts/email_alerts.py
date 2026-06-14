"""
Email Alert Service — sends severity-based email notifications.

Features:
- SMTP-based (Gmail, SendGrid, any SMTP server)
- Batches duplicate errors (deduplication window)
- Configurable per source + severity
- Includes link to dashboard
"""

import logging
import os
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Deduplication: track recent alerts to avoid spamming
_recent_alerts = defaultdict(list)  # key: (source, classification) → [timestamps]
DEDUP_WINDOW_MINUTES = 5


class EmailAlertService:
    """Sends email alerts for high-severity log classifications."""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("ALERT_FROM_EMAIL", self.smtp_user)
        self.dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:3000")
        self.enabled = bool(self.smtp_user and self.smtp_password)

        if self.enabled:
            logger.info("[EMAIL] Alert service initialized")
        else:
            logger.warning("[EMAIL] Alert service disabled — SMTP credentials not configured")

    def is_available(self) -> bool:
        return self.enabled

    def should_alert(self, source: str, classification: str, severity: str) -> bool:
        """Check if alert should fire (severity threshold + dedup)."""
        if not self.enabled:
            return False

        # Only alert on High and Critical
        if severity not in ("High", "Critical"):
            return False

        # Deduplication check
        key = (source or "unknown", classification)
        now = datetime.now()
        cutoff = now - timedelta(minutes=DEDUP_WINDOW_MINUTES)

        # Clean old entries
        _recent_alerts[key] = [t for t in _recent_alerts[key] if t > cutoff]

        if _recent_alerts[key]:
            logger.debug(f"[EMAIL] Dedup: alert for {key} already sent in last {DEDUP_WINDOW_MINUTES}m")
            return False

        _recent_alerts[key].append(now)
        return True

    def send_alert(
        self,
        to_email: str,
        log_text: str,
        classification: str,
        severity: str,
        source: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> bool:
        """Send an email alert for a classified log."""
        if not self.enabled:
            logger.warning("[EMAIL] Cannot send — service not configured")
            return False

        subject = f"[IntelliLog {severity}] {classification}"
        if source:
            subject += f" — {source}"

        body = self._build_email_body(
            log_text, classification, severity, source, confidence
        )

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"[EMAIL] Alert sent to {to_email} — {classification} ({severity})")
            return True

        except Exception as e:
            logger.error(f"[EMAIL] Failed to send alert: {e}")
            return False

    def _build_email_body(
        self,
        log_text: str,
        classification: str,
        severity: str,
        source: Optional[str],
        confidence: Optional[float]
    ) -> str:
        """Build HTML email body."""
        severity_color = {
            "Critical": "#dc3545",
            "High": "#fd7e14",
            "Medium": "#ffc107",
            "Low": "#28a745"
        }.get(severity, "#6c757d")

        return f"""
        <html>
        <body style="font-family: -apple-system, sans-serif; padding: 20px;">
            <h2 style="color: {severity_color};">⚠️ {severity} Alert: {classification}</h2>
            <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Source</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{source or 'Unknown'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Classification</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{classification}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Severity</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: {severity_color};">{severity}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Confidence</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{f'{confidence:.2%}' if confidence else 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Time</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <h3>Log Message</h3>
            <pre style="background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto;">{log_text[:500]}</pre>
            <p><a href="{self.dashboard_url}" style="color: #007bff;">View in Dashboard →</a></p>
            <hr style="border: none; border-top: 1px solid #eee;">
            <p style="color: #999; font-size: 12px;">Sent by IntelliLog AI Alert System</p>
        </body>
        </html>
        """
