import logging

from backend.stages.regex_engine import RegexEngine
from backend.ml.inference import MLInference
from backend.llm.groq_client import GroqLLM
from backend.ml.anomaly import AnomalyDetector
from backend.ml.drift import DriftDetector

logger = logging.getLogger(__name__)

# Severity mapping for ML predictions
# Regex stage has its own severity from rules; LLM stage returns severity from the model.
# This map ensures ML predictions get appropriate severity instead of always "Medium".
SEVERITY_MAP = {
    "Memory Leak": "Critical",
    "Disk Full": "Critical",
    "Kubernetes CrashLoop": "Critical",
    "Database Error": "High",
    "HTTP 500": "High",
    "SSL Error": "High",
    "DNS Failure": "High",
    "Redis Failure": "High",
    "Kafka Failure": "High",
    "Payment Failure": "High",
    "Authentication Failure": "Medium",
    "API Timeout": "Medium",
    "HTTP 403": "Medium",
    "HTTP 404": "Low",
    "CPU Spike": "Medium",
}


class LogRouter:

    def __init__(self):
        logger.info("[ROUTER] Initializing LogRouter pipeline")

        try:
            self.regex_engine = RegexEngine()
            logger.info("[ROUTER] Regex engine initialized")
        except Exception as e:
            logger.error(f"[ROUTER] Failed to initialize regex engine: {e}")
            self.regex_engine = None

        try:
            self.ml_engine = MLInference()
            logger.info("[ROUTER] ML engine initialized")
        except Exception as e:
            logger.error(f"[ROUTER] Failed to initialize ML engine: {e}")
            self.ml_engine = None

        try:
            self.llm_engine = GroqLLM()
            logger.info("[ROUTER] LLM engine initialized")
        except Exception as e:
            logger.warning(f"[ROUTER] Failed to initialize LLM engine: {e}")
            self.llm_engine = None

        # Anomaly Detection
        try:
            self.anomaly_detector = AnomalyDetector()
            logger.info("[ROUTER] Anomaly detector initialized")
        except Exception as e:
            logger.warning(f"[ROUTER] Failed to initialize anomaly detector: {e}")
            self.anomaly_detector = None

        # Drift Detection
        try:
            self.drift_detector = DriftDetector()
            logger.info("[ROUTER] Drift detector initialized")
        except Exception as e:
            logger.warning(f"[ROUTER] Failed to initialize drift detector: {e}")
            self.drift_detector = None

        logger.info("[ROUTER] Pipeline initialization complete")

    def process_log(self, log_text: str) -> dict:
        logger.info(f"[ROUTER] Processing log: {log_text[:80]}...")

        # =========================================
        # STEP 0 — ANOMALY DETECTION
        # =========================================

        anomaly_info = None
        if self.anomaly_detector and self.anomaly_detector.is_available():
            try:
                anomaly_info = self.anomaly_detector.score(log_text)

                if anomaly_info.get("is_anomaly"):
                    logger.warning(
                        f"[ROUTER] ANOMALY DETECTED — score: {anomaly_info['anomaly_score']}"
                    )
                    # Still classify it, but flag it as anomalous
            except Exception as e:
                logger.error(f"[ROUTER] Anomaly detection failed: {e}")

        # =========================================
        # STEP 1 — REGEX ENGINE
        # =========================================

        if self.regex_engine:
            try:
                regex_result = self.regex_engine.classify(log_text)

                if regex_result["matched"]:
                    logger.info("[ROUTER] Log resolved at Stage 1 (Regex)")

                    # Add anomaly info if available
                    if anomaly_info and anomaly_info.get("is_anomaly"):
                        regex_result["anomaly"] = True
                        regex_result["anomaly_score"] = anomaly_info["anomaly_score"]

                    # Record for drift detection
                    self._record_drift(
                        regex_result.get("classification"),
                        1.0,
                        "regex"
                    )

                    return regex_result

            except Exception as e:
                logger.error(f"[ROUTER] Regex engine failed: {e}")
        else:
            logger.warning("[ROUTER] Regex engine unavailable — skipping Stage 1")

        # =========================================
        # STEP 2 — ML INFERENCE
        # =========================================

        if not self.ml_engine:
            logger.error("[ROUTER] ML engine unavailable — cannot proceed")
            return {
                "matched": False,
                "error": "ML engine not available"
            }

        try:
            ml_result = self.ml_engine.predict(log_text)
            confidence = ml_result["confidence"]
            logger.info(f"[ROUTER] ML prediction: {ml_result['prediction']}, confidence: {confidence}")

        except Exception as e:
            logger.error(f"[ROUTER] ML inference failed: {e}")
            return {
                "matched": False,
                "error": f"ML inference failed: {str(e)}"
            }

        # =========================================
        # STEP 3 — HIGH CONFIDENCE ML (≥0.90)
        # =========================================

        if confidence >= 0.90:
            logger.info("[ROUTER] Log resolved at Stage 2 (ML — high confidence)")
            result = {
                "matched": True,
                "classification": ml_result["prediction"],
                "confidence": confidence,
                "severity": SEVERITY_MAP.get(ml_result["prediction"], "Medium"),
                "source": "ml-high-confidence"
            }
            if anomaly_info and anomaly_info.get("is_anomaly"):
                result["anomaly"] = True
                result["anomaly_score"] = anomaly_info["anomaly_score"]

            self._record_drift(ml_result["prediction"], confidence, "ml-high-confidence")
            return result

        # =========================================
        # STEP 4 — MEDIUM CONFIDENCE ML (≥0.70)
        # =========================================

        elif confidence >= 0.70:
            logger.info("[ROUTER] Log resolved at Stage 2 (ML — medium confidence)")
            result = {
                "matched": True,
                "classification": ml_result["prediction"],
                "confidence": confidence,
                "severity": SEVERITY_MAP.get(ml_result["prediction"], "Medium"),
                "warning": "Medium confidence prediction",
                "source": "ml-medium-confidence"
            }
            if anomaly_info and anomaly_info.get("is_anomaly"):
                result["anomaly"] = True
                result["anomaly_score"] = anomaly_info["anomaly_score"]

            self._record_drift(ml_result["prediction"], confidence, "ml-medium-confidence")
            return result

        # =========================================
        # STEP 5 — LOW CONFIDENCE (<0.70) → LLM ESCALATION
        # =========================================

        logger.info("[ROUTER] Low ML confidence — escalating to LLM (Stage 3)")

        if not self.llm_engine:
            logger.error("[ROUTER] LLM engine unavailable — cannot escalate")
            return {
                "matched": False,
                "error": "LLM engine not available, ML confidence too low",
                "ml_prediction": ml_result["prediction"],
                "confidence": confidence
            }

        try:
            llm_response = self.llm_engine.analyze_log(log_text)

        except Exception as e:
            logger.error(f"[ROUTER] LLM analysis failed: {e}")
            return {
                "matched": False,
                "error": f"LLM analysis failed: {str(e)}",
                "ml_prediction": ml_result["prediction"],
                "confidence": confidence
            }

        # =========================================
        # STEP 6 — LLM FAILED
        # =========================================

        if not llm_response.get("classification") or llm_response.get("classification") == "Unknown":
            logger.warning("[ROUTER] LLM returned no valid classification")
            return {
                "matched": False,
                "error": "Unable to classify log using any available engine."
            }

        # =========================================
        # STEP 7 — SUCCESSFUL LLM RESPONSE
        # =========================================

        logger.info(
            f"[ROUTER] Log resolved at Stage 3 (LLM) — "
            f"classification: {llm_response.get('classification')}"
        )

        result = {
            "matched": True,
            "classification": llm_response.get("classification", "Unknown"),
            "severity": llm_response.get("severity", "Unknown"),
            "root_cause": llm_response.get(
                "root_cause",
                llm_response.get("analysis", "")
            ),
            "solution": llm_response.get("solution", "Manual review required"),
            "source": "llm",
            "ml_confidence": confidence
        }

        if anomaly_info and anomaly_info.get("is_anomaly"):
            result["anomaly"] = True
            result["anomaly_score"] = anomaly_info["anomaly_score"]

        self._record_drift(
            llm_response.get("classification", "Unknown"),
            confidence,
            "llm"
        )

        return result

    def _record_drift(self, classification: str, confidence: float, source: str):
        """Record prediction data for drift detection."""
        if self.drift_detector:
            try:
                self.drift_detector.record(classification, confidence, source)
            except Exception as e:
                logger.debug(f"[ROUTER] Drift recording failed: {e}")
