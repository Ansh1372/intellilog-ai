"""
Log Retention & Cleanup — deletes old logs based on configurable retention period.

Usage:
    python -m backend.tasks.retention

Designed to run as a daily cron job.
"""

import logging
import os
from datetime import datetime, timedelta

from sqlalchemy import delete
from backend.database.db import SessionLocal
from backend.models.models import Log, Prediction, Feedback

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))


def cleanup_old_logs(retention_days: int = None) -> dict:
    """Delete logs older than retention period."""
    if retention_days is None:
        retention_days = DEFAULT_RETENTION_DAYS

    cutoff = datetime.now() - timedelta(days=retention_days)
    logger.info(f"[RETENTION] Cleaning logs older than {retention_days} days (before {cutoff})")

    db = SessionLocal()

    try:
        # Find old log IDs
        old_logs = db.query(Log.id).filter(Log.created_at < cutoff).all()
        old_log_ids = [log_id for (log_id,) in old_logs]

        if not old_log_ids:
            logger.info("[RETENTION] No logs to clean up")
            return {
                "status": "success",
                "deleted_logs": 0,
                "deleted_predictions": 0,
                "retention_days": retention_days
            }

        # Delete predictions for old logs
        pred_deleted = db.execute(
            delete(Prediction).where(Prediction.log_id.in_(old_log_ids))
        ).rowcount

        # Delete feedback for old logs
        feedback_deleted = db.execute(
            delete(Feedback).where(Feedback.log_id.in_(old_log_ids))
        ).rowcount

        # Delete old logs
        logs_deleted = db.execute(
            delete(Log).where(Log.id.in_(old_log_ids))
        ).rowcount

        db.commit()

        logger.info(
            f"[RETENTION] Cleaned up — logs: {logs_deleted}, "
            f"predictions: {pred_deleted}, feedback: {feedback_deleted}"
        )

        return {
            "status": "success",
            "deleted_logs": logs_deleted,
            "deleted_predictions": pred_deleted,
            "deleted_feedback": feedback_deleted,
            "retention_days": retention_days,
            "cutoff_date": str(cutoff)
        }

    except Exception as e:
        logger.error(f"[RETENTION] Cleanup failed: {e}")
        db.rollback()
        return {"status": "failed", "error": str(e)}

    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    result = cleanup_old_logs()
    print(f"Retention cleanup: {result}")
