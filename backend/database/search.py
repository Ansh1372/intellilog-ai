"""
Log Search Service — full-text search across classified logs.

Supports: text query, source filter, severity filter, time range, pagination.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.models import Log, Prediction

logger = logging.getLogger(__name__)


def search_logs(
    q: Optional[str] = None,
    source: Optional[str] = None,
    severity: Optional[str] = None,
    classification: Optional[str] = None,
    last: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: Session = None
) -> dict:
    """
    Search logs with filters.

    Args:
        q: Text search query (ILIKE on raw_log)
        source: Filter by source
        severity: Filter by severity
        classification: Filter by classification
        last: Time range (e.g., "1h", "7d", "24h", "30d")
        page: Page number
        limit: Results per page
        db: Database session
    """
    logger.info(f"[SEARCH] q={q}, source={source}, severity={severity}, last={last}")

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        query = db.query(Log, Prediction).join(
            Prediction, Log.id == Prediction.log_id
        )

        # Text search
        if q:
            query = query.filter(Log.raw_log.ilike(f"%{q}%"))

        # Source filter
        if source:
            query = query.filter(Log.source == source)

        # Severity filter
        if severity:
            query = query.filter(Prediction.severity == severity)

        # Classification filter
        if classification:
            query = query.filter(Prediction.classification == classification)

        # Time range filter
        if last:
            cutoff = _parse_time_range(last)
            if cutoff:
                query = query.filter(Log.created_at >= cutoff)

        # Get total count
        total = query.count()

        # Pagination
        offset = (page - 1) * limit
        results = query.order_by(Log.created_at.desc()).offset(offset).limit(limit).all()

        logs = []
        for log, prediction in results:
            logs.append({
                "log_id": log.id,
                "log": log.raw_log,
                "source": log.source,
                "classification": prediction.classification,
                "severity": prediction.severity,
                "confidence": prediction.confidence,
                "prediction_source": prediction.prediction_source,
                "created_at": str(log.created_at)
            })

        logger.info(f"[SEARCH] Found {total} results, returning page {page}")

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }

    except Exception as e:
        logger.error(f"[SEARCH] Search failed: {e}")
        return {"logs": [], "total": 0, "error": str(e)}

    finally:
        if should_close:
            db.close()


def _parse_time_range(last: str) -> Optional[datetime]:
    """Parse time range string like '1h', '7d', '24h', '30d'."""
    try:
        value = int(last[:-1])
        unit = last[-1].lower()

        if unit == "h":
            return datetime.now() - timedelta(hours=value)
        elif unit == "d":
            return datetime.now() - timedelta(days=value)
        elif unit == "m":
            return datetime.now() - timedelta(minutes=value)
        else:
            logger.warning(f"[SEARCH] Unknown time unit: {unit}")
            return None
    except (ValueError, IndexError):
        logger.warning(f"[SEARCH] Invalid time range: {last}")
        return None
