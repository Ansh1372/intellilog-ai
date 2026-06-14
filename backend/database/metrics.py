import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.models.models import Log, Prediction

logger = logging.getLogger(__name__)


def get_metrics(db: Session = None):
    """Get classification metrics from the database."""

    logger.info("[METRICS] Fetching classification metrics")

    should_close = False

    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        total_logs = db.query(Log).count()
        logger.debug(f"[METRICS] Total logs: {total_logs}")

        regex_hits = db.query(Prediction).filter(
            Prediction.prediction_source == "regex"
        ).count()

        ml_hits = db.query(Prediction).filter(
            Prediction.prediction_source.in_([
                "ml",
                "ml-high-confidence"
            ])
        ).count()

        llm_hits = db.query(Prediction).filter(
            Prediction.prediction_source == "llm"
        ).count()

        avg_confidence = db.query(
            func.avg(Prediction.confidence)
        ).scalar()

        logger.info(
            f"[METRICS] Results — total: {total_logs}, regex: {regex_hits}, "
            f"ml: {ml_hits}, llm: {llm_hits}, avg_confidence: {avg_confidence}"
        )

        return {
            "total_logs": total_logs,
            "regex_hits": regex_hits,
            "ml_hits": ml_hits,
            "llm_hits": llm_hits,
            "avg_confidence": round(avg_confidence or 0, 4)
        }

    except Exception as e:
        logger.error(f"[METRICS] Failed to fetch metrics: {e}")
        raise

    finally:
        if should_close:
            db.close()
            logger.debug("[METRICS] Database session closed")
