import logging

from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.models import Log, Prediction

logger = logging.getLogger(__name__)


def save_log_prediction(log_text: str, result: dict, source: str = None, db: Session = None):
    """Save log and its prediction to the database."""

    logger.info("[CRUD] Saving log prediction to database")
    logger.debug(f"[CRUD] Log text: {log_text[:80]}...")
    logger.debug(f"[CRUD] Result source: {result.get('source')}, user source: {source}")

    should_close = False

    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # SAVE RAW LOG (with source from request)
        log_entry = Log(raw_log=log_text, source=source)
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        logger.info(f"[CRUD] Log saved with id: {log_entry.id}, source: {source}")

        # SAVE PREDICTION
        prediction_entry = Prediction(
            log_id=log_entry.id,
            classification=result.get(
                "classification",
                result.get("source", "unknown")
            ),
            confidence=result.get(
                "confidence",
                result.get("ml_confidence")
            ),
            prediction_source=result.get("source", "unknown"),
            severity=result.get("severity"),
            reasoning=result.get("llm_analysis"),
            solution=result.get("solution")
        )

        db.add(prediction_entry)
        db.commit()
        logger.info(
            f"[CRUD] Prediction saved — classification: {prediction_entry.classification}, "
            f"source: {prediction_entry.prediction_source}"
        )

    except Exception as e:
        logger.error(f"[CRUD] Failed to save log prediction: {e}")
        db.rollback()
        raise

    finally:
        if should_close:
            db.close()
            logger.debug("[CRUD] Database session closed")
