"""
Drift Detection — monitors if incoming log distributions
are shifting away from training data.
Alerts when the model might need retraining.
"""

import os
import logging
import numpy as np
import joblib
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

DRIFT_WINDOW_SIZE = 100  # Track last N predictions
CONFIDENCE_ALERT_THRESHOLD = 0.75  # Alert if avg confidence drops below this
PSI_THRESHOLD = 0.2  # Population Stability Index threshold


class DriftDetector:

    def __init__(self):
        logger.info("[DRIFT] Initializing DriftDetector")

        # Rolling window of recent confidence scores
        self.confidence_window = deque(maxlen=DRIFT_WINDOW_SIZE)
        # Rolling window of recent classifications
        self.classification_window = deque(maxlen=DRIFT_WINDOW_SIZE)
        # Track prediction sources
        self.source_window = deque(maxlen=DRIFT_WINDOW_SIZE)
        # Timestamps
        self.timestamp_window = deque(maxlen=DRIFT_WINDOW_SIZE)

        # Training distribution (loaded from saved stats)
        self.training_class_distribution = None
        self._load_training_stats()

        logger.info("[DRIFT] DriftDetector initialized")

    def _load_training_stats(self):
        """Load training data class distribution for comparison."""
        stats_path = "models/training_stats.pkl"

        if os.path.exists(stats_path):
            try:
                self.training_class_distribution = joblib.load(stats_path)
                logger.info("[DRIFT] Training stats loaded")
            except Exception as e:
                logger.warning(f"[DRIFT] Failed to load training stats: {e}")
                self.training_class_distribution = None
        else:
            logger.info("[DRIFT] No training stats found — will compute on first check")

    def record(self, classification: str, confidence: float, source: str):
        """Record a new prediction for drift monitoring."""
        self.confidence_window.append(confidence if confidence else 0.0)
        self.classification_window.append(classification)
        self.source_window.append(source)
        self.timestamp_window.append(datetime.now().isoformat())

        logger.debug(
            f"[DRIFT] Recorded — class: {classification}, "
            f"conf: {confidence}, window size: {len(self.confidence_window)}"
        )

    def get_report(self) -> dict:
        """Generate a drift detection report."""
        logger.info("[DRIFT] Generating drift report")

        window_size = len(self.confidence_window)

        if window_size < 10:
            logger.info("[DRIFT] Not enough data for drift analysis")
            return {
                "status": "insufficient_data",
                "message": f"Need at least 10 predictions, have {window_size}",
                "window_size": window_size
            }

        # 1. Confidence trend
        confidences = list(self.confidence_window)
        avg_confidence = np.mean(confidences)
        recent_confidence = np.mean(confidences[-20:]) if len(confidences) >= 20 else avg_confidence
        confidence_declining = recent_confidence < avg_confidence - 0.05

        # 2. Class distribution of recent predictions
        classifications = list(self.classification_window)
        unique_classes, counts = np.unique(classifications, return_counts=True)
        current_distribution = {
            str(k): float(v) for k, v in zip(unique_classes, counts / len(classifications))
        }

        # 3. PSI calculation (if training stats available)
        psi_score = None
        if self.training_class_distribution:
            psi_score = self._calculate_psi(current_distribution)

        # 4. Source distribution
        sources = list(self.source_window)
        unique_sources, source_counts = np.unique(sources, return_counts=True)
        source_distribution = {str(k): int(v) for k, v in zip(unique_sources, source_counts)}

        # LLM escalation rate
        llm_count = source_distribution.get("llm", 0)
        llm_rate = llm_count / window_size if window_size > 0 else 0

        # 5. Determine recommendation
        recommendation = self._get_recommendation(
            avg_confidence, confidence_declining, psi_score, llm_rate
        )

        report = {
            "status": "ok",
            "window_size": int(window_size),
            "avg_confidence": round(float(avg_confidence), 4),
            "recent_confidence": round(float(recent_confidence), 4),
            "confidence_declining": bool(confidence_declining),
            "class_distribution": current_distribution,
            "source_distribution": source_distribution,
            "llm_escalation_rate": round(float(llm_rate), 4),
            "psi_score": round(float(psi_score), 4) if psi_score is not None else None,
            "data_drift_detected": bool(psi_score > PSI_THRESHOLD) if psi_score else False,
            "recommendation": recommendation,
            "generated_at": datetime.now().isoformat()
        }

        logger.info(
            f"[DRIFT] Report — avg_conf: {avg_confidence:.4f}, "
            f"drift: {report['data_drift_detected']}, "
            f"recommendation: {recommendation}"
        )

        return report

    def _calculate_psi(self, current_dist: dict) -> float:
        """
        Calculate Population Stability Index between training and current distributions.
        PSI < 0.1 = no drift, 0.1-0.2 = moderate, > 0.2 = significant drift.
        """
        psi = 0.0
        all_classes = set(list(self.training_class_distribution.keys()) + list(current_dist.keys()))

        for cls in all_classes:
            # Use small epsilon to avoid division by zero
            expected = self.training_class_distribution.get(cls, 0.001)
            actual = current_dist.get(cls, 0.001)

            # Clamp to avoid log(0)
            expected = max(expected, 0.001)
            actual = max(actual, 0.001)

            psi += (actual - expected) * np.log(actual / expected)

        return abs(psi)

    def _get_recommendation(
        self,
        avg_confidence: float,
        confidence_declining: bool,
        psi_score: float,
        llm_rate: float
    ) -> str:
        """Determine action recommendation based on drift signals."""

        if psi_score and psi_score > PSI_THRESHOLD:
            return "retrain_recommended"
        if avg_confidence < CONFIDENCE_ALERT_THRESHOLD:
            return "retrain_recommended"
        if llm_rate > 0.2:
            return "retrain_recommended"
        if confidence_declining:
            return "monitor"
        if llm_rate > 0.1:
            return "monitor"
        return "stable"
