"""
Syslog UDP Listener — receives logs on UDP 514, classifies, and stores them.

Usage:
    python -m backend.ingest.syslog_listener

Receives syslog messages, extracts source from syslog tag, classifies via pipeline.
"""

import logging
import socketserver
import re
import threading
from datetime import datetime

from backend.router import LogRouter
from backend.database.crud import save_log_prediction
from backend.database.db import SessionLocal

logger = logging.getLogger(__name__)

SYSLOG_PORT = 514
SYSLOG_HOST = "0.0.0.0"

# Syslog format: <priority>timestamp hostname tag[pid]: message
SYSLOG_PATTERN = re.compile(
    r"^(?:<\d+>)?"                    # optional priority
    r"(?:\w{3}\s+\d+\s+\d+:\d+:\d+\s+)?"  # optional timestamp
    r"(?P<hostname>\S+)\s+"           # hostname
    r"(?P<tag>\S+?)(?:\[\d+\])?:\s*"  # tag (source) with optional PID
    r"(?P<message>.+)$"              # message
)


class SyslogHandler(socketserver.BaseRequestHandler):
    """Handles incoming syslog UDP messages."""

    def handle(self):
        data = self.request[0].strip()
        try:
            message = data.decode("utf-8", errors="ignore")
        except Exception:
            return

        if not message or len(message) < 5:
            return

        # Parse syslog format
        source, log_text = self._parse_syslog(message)

        logger.info(f"[SYSLOG] Received from {self.client_address[0]} — source: {source}")
        logger.debug(f"[SYSLOG] Message: {log_text[:100]}")

        # Classify
        try:
            router = self.server.router
            if router is None:
                logger.error("[SYSLOG] Router not available, dropping log")
                return

            result = router.process_log(log_text)

            # Save to DB
            db = SessionLocal()
            try:
                save_log_prediction(log_text, result, source=source, db=db)
            finally:
                db.close()

            logger.debug(f"[SYSLOG] Classified as: {result.get('classification', 'unknown')}")

        except Exception as e:
            logger.error(f"[SYSLOG] Error processing message: {e}")

    def _parse_syslog(self, raw_message: str) -> tuple:
        """Parse syslog message, return (source, log_text)."""
        match = SYSLOG_PATTERN.match(raw_message)
        if match:
            source = match.group("tag")
            message = match.group("message")
            return source, message
        # Fallback: use full message, unknown source
        return "syslog", raw_message


class SyslogUDPServer(socketserver.UDPServer):
    """UDP server with router reference."""

    def __init__(self, server_address, handler, router):
        self.router = router
        super().__init__(server_address, handler)


def start_syslog_listener(host: str = SYSLOG_HOST, port: int = SYSLOG_PORT, router=None):
    """Start the syslog UDP listener in a thread."""
    if router is None:
        try:
            router = LogRouter()
        except Exception as e:
            logger.error(f"[SYSLOG] Failed to initialize router: {e}")
            return None

    try:
        server = SyslogUDPServer((host, port), SyslogHandler, router)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"[SYSLOG] Listening on UDP {host}:{port}")
        return server
    except PermissionError:
        logger.error(f"[SYSLOG] Permission denied on port {port}. Try port > 1024 or run as root.")
        return None
    except Exception as e:
        logger.error(f"[SYSLOG] Failed to start listener: {e}")
        return None


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    logger.info("[SYSLOG] Starting syslog listener as standalone service")
    router = LogRouter()
    server = start_syslog_listener(port=5514, router=router)  # Use 5514 to avoid root requirement
    if server:
        logger.info("[SYSLOG] Press Ctrl+C to stop")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
            logger.info("[SYSLOG] Stopped")
