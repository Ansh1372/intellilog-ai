"""
Retrain the ML model using a user-uploaded CSV file.
Combines uploaded data with original training data for better generalization.
"""

import logging
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

logger = logging.getLogger(__name__)

MIN_SAMPLES_REQUIRED = 20


def retrain_from_uploaded_file(csv_path: str, combine_with_original: bool = True) -> dict:
    """
    Retrain model from an uploaded CSV file.

    Args:
        csv_path: Path to the uploaded CSV (must have 'log_text' and 'label' columns)
        combine_with_original: Whether to merge with existing training data
    """
    logger.info(f"[RETRAIN-FILE] Starting retraining from: {csv_path}")

    try:
        uploaded_df = pd.read_csv(csv_path)
        uploaded_df = uploaded_df.dropna(subset=["log_text", "label"])
        uploaded_df["log_text"] = uploaded_df["log_text"].fillna("")
        logger.info(f"[RETRAIN-FILE] Uploaded data: {len(uploaded_df)} rows")

        # Optionally combine with original training data
        if combine_with_original:
            try:
                original_df = pd.read_csv("data/advanced_train_logs.csv")
                combined_df = pd.concat([original_df, uploaded_df], ignore_index=True)
                combined_df = combined_df.dropna(subset=["log_text", "label"])
                combined_df["log_text"] = combined_df["log_text"].fillna("")
                logger.info(f"[RETRAIN-FILE] Combined data: {len(combined_df)} rows")
            except FileNotFoundError:
                logger.warning("[RETRAIN-FILE] Original data not found, using uploaded only")
                combined_df = uploaded_df
        else:
            combined_df = uploaded_df

        if len(combined_df) < MIN_SAMPLES_REQUIRED:
            return {
                "status": "failed",
                "error": f"Not enough data. Need {MIN_SAMPLES_REQUIRED}, got {len(combined_df)}"
            }

        # Train
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

        logger.info(f"[RETRAIN-FILE] New model accuracy: {accuracy:.4f}")

        # Save
        joblib.dump(model, "models/model.pkl")
        joblib.dump(vectorizer, "models/vectorizer.pkl")
        logger.info("[RETRAIN-FILE] Model saved")

        return {
            "status": "success",
            "total_training_samples": len(combined_df),
            "uploaded_samples": len(uploaded_df),
            "accuracy": round(accuracy, 4),
            "classes": list(y.unique()),
            "message": "Model retrained successfully with uploaded data"
        }

    except Exception as e:
        logger.error(f"[RETRAIN-FILE] Failed: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }
