"""
Log Correlation — groups critical errors from multiple sources in the same time window.

When multiple sources spike critical errors in the same 5-minute window,
groups them as one "incident".
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.models import Log, Prediction, Incident

logger = logging.getLogger(__name__)

CORRELATION_WINDOW_MINUTES = 5
MIN_SOURCES_FOR_INCIDENT = 2


def detect_incidents(window_minutes: int = CORRELATION_WINDOW_MINUTES, db: Session = None) -> dict:
    """
    Check for correlated critical errors across sources in the last time window.
    Returns any detected incidents.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        window_start = datetime.now() - timedelta(minutes=window_minutes)

        # Find critical/high severity logs in the window, grouped by source
        critical_by_source = db.query(
            Log.source,
            func.count(Log.id).label("count"),
            func.array_agg(Log.id).label("log_ids")
        ).join(
            Prediction, Log.id == Prediction.log_id
        ).filter(
            Log.created_at >= window_start,
            Prediction.severity.in_(["Critical", "High"]),
            Log.source.isnot(None)
        ).group_by(Log.source).all()

        if len(critical_by_source) < MIN_SOURCES_FOR_INCIDENT:
            return {"incidents": [], "message": "No correlated incidents detected"}

        # Multiple sources have critical errors → create incident
        sources = [row.source for row in critical_by_source]
        all_log_ids = []
        for row in critical_by_source:
            if row.log_ids:
                all_log_ids.extend(row.log_ids)

        incident = Incident(
            sources=sources,
            severity="Critical",
            log_ids=all_log_ids[:100],  # Cap at 100 log IDs
            window_start=window_start,
            window_end=datetime.now(),
            resolved=False
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        logger.warning(
            f"[CORRELATION] Incident detected — {len(sources)} sources: {sources}"
        )

        return {
            "incidents": [{
                "incident_id": incident.id,
                "sources": sources,
                "severity": "Critical",
                "log_count": len(all_log_ids),
                "window": f"{window_minutes} minutes",
                "detected_at": datetime.now().isoformat()
            }],
            "message": f"Incident detected: {len(sources)} sources spiking critical errors"
        }

    except Exception as e:
        logger.error(f"[CORRELATION] Detection failed: {e}")
        db.rollback()
        return {"incidents": [], "error": str(e)}

    finally:
        if should_close:
            db.close()


def get_recent_incidents(limit: int = 10, db: Session = None) -> list:
    """Get recent incidents."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        incidents = db.query(Incident).order_by(
            Incident.created_at.desc()
        ).limit(limit).all()

        return [{
            "incident_id": inc.id,
            "sources": inc.sources,
            "severity": inc.severity,
            "log_count": len(inc.log_ids) if inc.log_ids else 0,
            "window_start": str(inc.window_start),
            "window_end": str(inc.window_end),
            "resolved": inc.resolved,
            "created_at": str(inc.created_at)
        } for inc in incidents]

    except Exception as e:
        logger.error(f"[CORRELATION] Failed to fetch incidents: {e}")
        return []

    finally:
        if should_close:
            db.close()
