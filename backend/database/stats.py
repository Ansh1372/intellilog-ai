"""
Per-Source Stats — returns metrics for a specific source.

Powers the dashboard health cards.
"""

import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.models import Log, Prediction

logger = logging.getLogger(__name__)


def get_source_stats(source: Optional[str] = None, db: Session = None) -> dict:
    """
    Get stats for a specific source or all sources.

    Returns: total logs, error rate, most common category, last error timestamp.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        query = db.query(Log, Prediction).join(
            Prediction, Log.id == Prediction.log_id
        )

        if source:
            query = query.filter(Log.source == source)

        total = query.count()

        if total == 0:
            return {
                "source": source,
                "total_logs": 0,
                "error_rate": 0,
                "most_common_category": None,
                "last_error_at": None
            }

        # Error rate (High + Critical severity)
        error_count = query.filter(
            Prediction.severity.in_(["High", "Critical"])
        ).count()
        error_rate = round(error_count / total, 4) if total > 0 else 0

        # Most common classification
        top_classification = db.query(
            Prediction.classification,
            func.count(Prediction.id).label("cnt")
        ).join(Log, Log.id == Prediction.log_id)

        if source:
            top_classification = top_classification.filter(Log.source == source)

        top_classification = top_classification.group_by(
            Prediction.classification
        ).order_by(func.count(Prediction.id).desc()).first()

        most_common = top_classification[0] if top_classification else None

        # Last error timestamp
        last_error = query.filter(
            Prediction.severity.in_(["High", "Critical"])
        ).order_by(Log.created_at.desc()).first()

        last_error_at = str(last_error[0].created_at) if last_error else None

        # Severity distribution
        severity_dist = db.query(
            Prediction.severity,
            func.count(Prediction.id)
        ).join(Log, Log.id == Prediction.log_id)

        if source:
            severity_dist = severity_dist.filter(Log.source == source)

        severity_dist = severity_dist.group_by(Prediction.severity).all()
        severity_map = {s: c for s, c in severity_dist if s}

        return {
            "source": source or "all",
            "total_logs": total,
            "error_rate": error_rate,
            "error_count": error_count,
            "most_common_category": most_common,
            "last_error_at": last_error_at,
            "severity_distribution": severity_map
        }

    except Exception as e:
        logger.error(f"[STATS] Failed to get stats: {e}")
        return {"error": str(e)}

    finally:
        if should_close:
            db.close()


def get_all_sources(db: Session = None) -> list:
    """Get list of all unique sources."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        sources = db.query(Log.source).filter(
            Log.source.isnot(None)
        ).distinct().all()
        return [s[0] for s in sources]

    except Exception as e:
        logger.error(f"[STATS] Failed to get sources: {e}")
        return []

    finally:
        if should_close:
            db.close()
