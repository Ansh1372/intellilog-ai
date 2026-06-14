"""
Anomaly Detection for IntelliLog AI.
Combines Isolation Forest with ML confidence entropy to detect
novel/unknown log patterns that don't fit any known category.

Strategy:
- Isolation Forest detects structural anomalies in known vocabulary space
- Entropy of ML prediction probabilities detects uncertain patterns
- A log is anomalous if it has HIGH entropy (ML is confused) AND
  it maps to mostly unknown vocabulary (low TF-IDF feature activation)
"""

import os
import logging
import joblib
import numpy as np

logger = logging.getLogger(__name__)

ANOMALY_MODEL_PATH = "models/anomaly_model.pkl"
ENTROPY_THRESHOLD = 2.0  # High entropy = ML is confused across many classes
FEATURE_ACTIVATION_THRESHOLD = 0.25  # Low activation = mostly unknown words


class AnomalyDetector:

    def __init__(self):
        logger.info("[ANOMALY] Initializing AnomalyDetector")

        self.model = None
        self.vectorizer = None
        self.ml_model = None

        # Load Isolation Forest
        if not os.path.exists(ANOMALY_MODEL_PATH):
            logger.warning(
                f"[ANOMALY] Model not found at {ANOMALY_MODEL_PATH}. "
                "Run train_anomaly.py first. Anomaly detection disabled."
            )
            return

        try:
            self.model = joblib.load(ANOMALY_MODEL_PATH)

            vectorizer_path = "models/vectorizer.pkl"
            ml_model_path = "models/model.pkl"

            if os.path.exists(vectorizer_path):
                self.vectorizer = joblib.load(vectorizer_path)
            else:
                logger.error("[ANOMALY] Vectorizer not found")
                self.model = None
                return

            if os.path.exists(ml_model_path):
                self.ml_model = joblib.load(ml_model_path)
            else:
                logger.warning("[ANOMALY] ML model not found — using isolation forest only")

            logger.info("[ANOMALY] Model and vectorizer loaded successfully")

        except Exception as e:
            logger.error(f"[ANOMALY] Failed to load model: {e}")
            self.model = None
            self.vectorizer = None

    def is_available(self) -> bool:
        return self.model is not None and self.vectorizer is not None

    def score(self, log_text: str) -> dict:
        """
        Score a log for anomaly detection.
        Uses entropy of ML predictions + TF-IDF feature activation.
        """
        if not self.is_available():
            logger.debug("[ANOMALY] Detector not available, skipping")
            return {"is_anomaly": False, "anomaly_score": None, "available": False}

        try:
            vectorized = self.vectorizer.transform([log_text])

            # 1. Feature activation — how much of the log maps to known vocabulary
            feature_activation = vectorized.sum() / max(len(log_text.split()), 1)
            low_activation = float(feature_activation) < FEATURE_ACTIVATION_THRESHOLD

            # 2. Prediction entropy — how uncertain is the ML model
            entropy = 0.0
            if self.ml_model is not None:
                probabilities = self.ml_model.predict_proba(vectorized)[0]
                # Shannon entropy (higher = more uncertain)
                probabilities = probabilities[probabilities > 0]
                entropy = -np.sum(probabilities * np.log2(probabilities))
                high_entropy = entropy > ENTROPY_THRESHOLD
            else:
                high_entropy = False

            # 3. Isolation Forest score
            iso_score = self.model.decision_function(vectorized)[0]

            # Combined anomaly decision:
            # Anomalous if ML is confused AND low vocabulary match
            is_anomaly = high_entropy and low_activation

            # Composite anomaly score (lower = more anomalous)
            # Normalize: invert entropy so lower score = more anomaly
            anomaly_score = round(float(1.0 - (entropy / 4.0)), 4)  # 4.0 = max entropy for 15 classes
            anomaly_score = max(-1.0, min(1.0, anomaly_score))

            logger.info(
                f"[ANOMALY] entropy: {entropy:.4f}, "
                f"feature_activation: {float(feature_activation):.4f}, "
                f"iso_score: {iso_score:.4f}, "
                f"is_anomaly: {is_anomaly}"
            )

            return {
                "is_anomaly": bool(is_anomaly),
                "anomaly_score": anomaly_score,
                "entropy": round(float(entropy), 4),
                "feature_activation": round(float(feature_activation), 4),
                "available": True
            }

        except Exception as e:
            logger.error(f"[ANOMALY] Scoring failed: {e}")
            return {"is_anomaly": False, "anomaly_score": None, "error": str(e), "available": True}

    def reload(self):
        """Reload the anomaly model from disk."""
        logger.info("[ANOMALY] Reloading model")
        self.__init__()
