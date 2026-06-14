"""
Feedback Service — stores user corrections for the feedback loop.

Used by "Mark Wrong" button in dashboard. Fed into daily retrain cron.
"""

import logging
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.models import Feedback, Prediction

logger = logging.getLogger(__name__)


def save_feedback(log_id: int, correct_label: str, db: Session = None) -> dict:
    """Save a user correction for a classified log."""
    logger.info(f"[FEEDBACK] Saving correction for log_id={log_id}: {correct_label}")

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # Get original prediction
        prediction = db.query(Prediction).filter(
            Prediction.log_id == log_id
        ).first()

        original_label = prediction.classification if prediction else None

        feedback_entry = Feedback(
            log_id=log_id,
            original_label=original_label,
            correct_label=correct_label
        )
        db.add(feedback_entry)
        db.commit()
        db.refresh(feedback_entry)

        logger.info(
            f"[FEEDBACK] Saved — log_id={log_id}, "
            f"original='{original_label}' → corrected='{correct_label}'"
        )

        return {
            "status": "success",
            "feedback_id": feedback_entry.id,
            "log_id": log_id,
            "original_label": original_label,
            "correct_label": correct_label
        }

    except Exception as e:
        logger.error(f"[FEEDBACK] Failed to save: {e}")
        db.rollback()
        return {"status": "failed", "error": str(e)}

    finally:
        if should_close:
            db.close()


def get_feedback_stats(db: Session = None) -> dict:
    """Get feedback statistics."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        total = db.query(Feedback).count()
        return {
            "total_corrections": total,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"[FEEDBACK] Failed to get stats: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        if should_close:
            db.close()
