import logging

from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.database.db import SessionLocal
from backend.models.models import Log, Prediction

logger = logging.getLogger(__name__)


class DashboardService:

    def get_recent_logs(self, db: Session = None, page: int = 1, limit: int = 50):
        """Get recent classified logs with pagination."""

        logger.info(f"[DASHBOARD] Fetching recent logs — page={page}, limit={limit}")

        should_close = False

        if db is None:
            db = SessionLocal()
            should_close = True

        offset = (page - 1) * limit

        try:
            # Get total count for pagination metadata
            total_count = db.query(Log).join(
                Prediction, Log.id == Prediction.log_id
            ).count()

            recent_logs = db.query(
                Log,
                Prediction
            ).join(
                Prediction,
                Log.id == Prediction.log_id
            ).order_by(
                Log.created_at.desc()
            ).offset(offset).limit(limit).all()

            results = []

            for log, prediction in recent_logs:
                results.append({
                    "log_id": log.id,
                    "log": log.raw_log,
                    "source": log.source,
                    "classification": prediction.classification,
                    "severity": prediction.severity,
                    "prediction_source": prediction.prediction_source,
                    "confidence": prediction.confidence,
                    "created_at": str(log.created_at)
                })

            logger.info(f"[DASHBOARD] Returned {len(results)} logs (page {page})")
            return {
                "logs": results,
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": (total_count + limit - 1) // limit
            }

        except Exception as e:
            logger.error(f"[DASHBOARD] Failed to fetch recent logs: {e}")
            raise

        finally:
            if should_close:
                db.close()
                logger.debug("[DASHBOARD] Database session closed")

    def get_metrics(self, db: Session = None):
        """Get dashboard metrics with stage breakdown."""

        logger.info("[DASHBOARD] Fetching dashboard metrics")

        should_close = False

        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            total_logs = db.query(Log).count()

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

            # TOP CLASSIFICATIONS
            top_classifications = db.query(
                Prediction.classification,
                func.count(Prediction.id)
            ).group_by(
                Prediction.classification
            ).order_by(
                func.count(Prediction.id).desc()
            ).limit(5).all()

            top_errors = []
            for item in top_classifications:
                top_errors.append({
                    "classification": item[0],
                    "count": item[1]
                })

            # SEVERITY DISTRIBUTION
            severity_data = db.query(
                Prediction.severity,
                func.count(Prediction.id)
            ).group_by(
                Prediction.severity
            ).all()

            severity_distribution = {}
            for severity, count in severity_data:
                severity_distribution[
                    severity if severity else "Unknown"
                ] = count

            logger.info(
                f"[DASHBOARD] Metrics — total: {total_logs}, regex: {regex_hits}, "
                f"ml: {ml_hits}, llm: {llm_hits}"
            )

            return {
                "total_logs": total_logs,
                "regex_hits": regex_hits,
                "ml_hits": ml_hits,
                "llm_hits": llm_hits,
                "avg_confidence": round(avg_confidence or 0, 4),
                "top_classifications": top_errors,
                "severity_distribution": severity_distribution
            }

        except Exception as e:
            logger.error(f"[DASHBOARD] Failed to fetch dashboard metrics: {e}")
            raise

        finally:
            if should_close:
                db.close()
                logger.debug("[DASHBOARD] Database session closed")
