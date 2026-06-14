"""
JSON Log Auto-Parser — extracts message and source from structured JSON logs.

If incoming log is valid JSON, extracts msg/message field for classification.
Auto-sets source from service/source field in the JSON.
Zero extra config — it just works.
"""

import logging
import json
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def try_parse_json_log(log_text: str) -> Tuple[str, Optional[str]]:
    """
    Attempt to parse a log line as JSON.

    Returns:
        (message_to_classify, extracted_source)

    If not JSON or no message field found, returns original text and None.
    """
    if not log_text or not log_text.strip().startswith("{"):
        return log_text, None

    try:
        data = json.loads(log_text)
    except (json.JSONDecodeError, TypeError):
        return log_text, None

    if not isinstance(data, dict):
        return log_text, None

    # Extract message field (common field names)
    message = None
    message_keys = ["msg", "message", "log", "text", "error", "description"]
    for key in message_keys:
        if key in data and isinstance(data[key], str) and data[key].strip():
            message = data[key]
            break

    # If no message found, use the full JSON as-is
    if not message:
        return log_text, None

    # Extract source field
    source = None
    source_keys = ["source", "service", "app", "application", "component", "container"]
    for key in source_keys:
        if key in data and isinstance(data[key], str) and data[key].strip():
            source = data[key]
            break

    # Optionally enrich message with level/severity info
    level = data.get("level") or data.get("severity") or data.get("loglevel")
    if level and isinstance(level, str):
        message = f"[{level.upper()}] {message}"

    logger.debug(f"[JSON-PARSE] Extracted — message: {message[:80]}, source: {source}")

    return message, source
