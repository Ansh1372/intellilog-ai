"""
Retrain the ML model using classified logs stored in the database.
This creates a feedback loop — the more logs classified, the better the model gets.
"""

import logging
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from backend.database.db import SessionLocal
from backend.models.models import Log, Prediction

logger = logging.getLogger(__name__)

MIN_SAMPLES_REQUIRED = 50


def retrain_model() -> dict:
    """Retrain ML model from database predictions + original training data."""

    logger.info("[RETRAIN] Starting model retraining process")

    db = SessionLocal()

    try:
        # Fetch classified logs from database (only high-confidence ones)
        logger.info("[RETRAIN] Fetching classified logs from database")

        db_records = db.query(
            Log.raw_log,
            Prediction.classification
        ).join(
            Prediction,
            Log.id == Prediction.log_id
        ).filter(
            Prediction.confidence >= 0.85,
            Prediction.classification.isnot(None)
        ).all()

        logger.info(f"[RETRAIN] Found {len(db_records)} high-confidence DB records")

        # Load original training data
        logger.info("[RETRAIN] Loading original training data")
        try:
            original_df = pd.read_csv("data/advanced_train_logs.csv")
            logger.info(f"[RETRAIN] Original data: {len(original_df)} records")
        except FileNotFoundError:
            logger.warning("[RETRAIN] Original training data not found, using DB only")
            original_df = pd.DataFrame(columns=["log_text", "label"])

        # Combine DB records with original data
        db_df = pd.DataFrame(db_records, columns=["log_text", "label"])

        combined_df = pd.concat([original_df, db_df], ignore_index=True)
        combined_df = combined_df.dropna(subset=["log_text", "label"])
        combined_df["log_text"] = combined_df["log_text"].fillna("")

        total_samples = len(combined_df)
        logger.info(f"[RETRAIN] Total training samples: {total_samples}")

        if total_samples < MIN_SAMPLES_REQUIRED:
            logger.warning(f"[RETRAIN] Not enough data ({total_samples} < {MIN_SAMPLES_REQUIRED})")
            return {
                "status": "skipped",
                "reason": f"Not enough training data. Need {MIN_SAMPLES_REQUIRED}, have {total_samples}",
                "db_records": len(db_records)
            }

        # Train new model
        logger.info("[RETRAIN] Training new model")

        X = combined_df["log_text"]
        y = combined_df["label"]

        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000)
        X_vectorized = vectorizer.fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(
            X_vectorized, y, test_size=0.2, random_state=42
        )

        model = LogisticRegression(max_iter=200)
        model.fit(X_train, y_train)

        # Evaluate
        predictions = model.predict(X_test)
        report = classification_report(y_test, predictions, output_dict=True)
        accuracy = report["accuracy"]

        logger.info(f"[RETRAIN] New model accuracy: {accuracy:.4f}")

        # Save model
        joblib.dump(model, "models/model.pkl")
        joblib.dump(vectorizer, "models/vectorizer.pkl")
        logger.info("[RETRAIN] Model and vectorizer saved successfully")

        return {
            "status": "success",
            "total_training_samples": total_samples,
            "db_records_used": len(db_records),
            "original_data_used": len(original_df),
            "accuracy": round(accuracy, 4),
            "classes": list(y.unique())
        }

    except Exception as e:
        logger.error(f"[RETRAIN] Retraining failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

    finally:
        db.close()
        logger.debug("[RETRAIN] Database session closed")
