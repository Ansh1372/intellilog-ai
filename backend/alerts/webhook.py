"""
Webhook Notification Service — sends POST requests to configured URLs on alert.

Covers Slack, Discord, PagerDuty, custom scripts — one feature, all integrations.
"""

import logging
import httpx
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT = 10  # seconds


class WebhookService:
    """Sends webhook notifications for classified logs."""

    def send_webhook(
        self,
        url: str,
        log_text: str,
        classification: str,
        severity: str,
        source: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> bool:
        """Send a webhook POST to the configured URL."""
        payload = {
            "event": "log_alert",
            "timestamp": datetime.now().isoformat(),
            "classification": classification,
            "severity": severity,
            "source": source or "unknown",
            "confidence": confidence,
            "log": log_text[:1000],  # Truncate for payload size
            "service": "IntelliLog AI"
        }

        try:
            with httpx.Client(timeout=WEBHOOK_TIMEOUT) as client:
                response = client.post(url, json=payload)

            if response.status_code < 300:
                logger.info(f"[WEBHOOK] Sent to {url} — status {response.status_code}")
                return True
            else:
                logger.warning(
                    f"[WEBHOOK] Non-success response from {url}: {response.status_code}"
                )
                return False

        except httpx.TimeoutException:
            logger.error(f"[WEBHOOK] Timeout sending to {url}")
            return False
        except Exception as e:
            logger.error(f"[WEBHOOK] Failed to send to {url}: {e}")
            return False
