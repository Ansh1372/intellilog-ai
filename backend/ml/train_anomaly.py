"""
Train Isolation Forest anomaly detection model.
Uses existing training data to learn "normal" log patterns.
Anything that deviates significantly from training distribution = anomaly.
"""

import logging
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import IsolationForest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

ANOMALY_MODEL_PATH = "models/anomaly_model.pkl"
VECTORIZER_PATH = "models/vectorizer.pkl"
TRAINING_DATA_PATH = "data/advanced_train_logs.csv"


def train_anomaly_model():
    """Train Isolation Forest on existing labeled data."""

    logger.info("[TRAIN-ANOMALY] Starting anomaly model training")

    # Load training data
    try:
        df = pd.read_csv(TRAINING_DATA_PATH)
        df = df.dropna(subset=["log_text"])
        logger.info(f"[TRAIN-ANOMALY] Loaded {len(df)} training samples")
    except FileNotFoundError:
        logger.error(f"[TRAIN-ANOMALY] Training data not found: {TRAINING_DATA_PATH}")
        return {"status": "failed", "error": "Training data not found"}

    # Load existing vectorizer (same one used by ML classifier)
    try:
        vectorizer = joblib.load(VECTORIZER_PATH)
        logger.info("[TRAIN-ANOMALY] Loaded existing TF-IDF vectorizer")
    except FileNotFoundError:
        logger.error(f"[TRAIN-ANOMALY] Vectorizer not found: {VECTORIZER_PATH}")
        return {"status": "failed", "error": "Vectorizer not found. Train ML model first."}

    # Vectorize training data
    X = vectorizer.transform(df["log_text"].fillna(""))
    logger.info(f"[TRAIN-ANOMALY] Vectorized shape: {X.shape}")

    # Train Isolation Forest
    # contamination=0.05 means we expect ~5% of training data could be noisy
    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X)

    # Get score statistics for reference
    scores = model.decision_function(X)
    logger.info(
        f"[TRAIN-ANOMALY] Score stats — "
        f"mean: {np.mean(scores):.4f}, "
        f"std: {np.std(scores):.4f}, "
        f"min: {np.min(scores):.4f}, "
        f"max: {np.max(scores):.4f}"
    )

    # Save model
    joblib.dump(model, ANOMALY_MODEL_PATH)
    logger.info(f"[TRAIN-ANOMALY] Model saved to {ANOMALY_MODEL_PATH}")

    return {
        "status": "success",
        "training_samples": len(df),
        "score_mean": round(float(np.mean(scores)), 4),
        "score_std": round(float(np.std(scores)), 4),
        "model_path": ANOMALY_MODEL_PATH
    }


if __name__ == "__main__":
    result = train_anomaly_model()
    print(f"\nResult: {result}")
