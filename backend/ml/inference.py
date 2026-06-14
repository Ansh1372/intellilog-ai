import os
import logging
import joblib

logger = logging.getLogger(__name__)


class MLInference:

    def __init__(self):
        model_path = os.path.join("models", "model.pkl")
        vectorizer_path = os.path.join("models", "vectorizer.pkl")

        logger.info(f"[ML] Initializing MLInference — model: {model_path}")

        if not os.path.exists(model_path):
            logger.error(f"[ML] Model file not found: {model_path}")
            raise FileNotFoundError(
                f"ML model not found at '{model_path}'. Run train_model.py first."
            )

        if not os.path.exists(vectorizer_path):
            logger.error(f"[ML] Vectorizer file not found: {vectorizer_path}")
            raise FileNotFoundError(
                f"Vectorizer not found at '{vectorizer_path}'. Run train_model.py first."
            )

        try:
            self.model = joblib.load(model_path)
            self.vectorizer = joblib.load(vectorizer_path)
            logger.info("[ML] Model and vectorizer loaded successfully")

        except Exception as e:
            logger.error(f"[ML] Failed to load model/vectorizer: {e}")
            raise

    def predict(self, log_text: str) -> dict:
        logger.debug(f"[ML] Predicting for log: {log_text[:80]}...")

        try:
            vectorized_text = self.vectorizer.transform([log_text])

            prediction = self.model.predict(vectorized_text)[0]
            probabilities = self.model.predict_proba(vectorized_text)[0]
            confidence = max(probabilities)

            logger.info(
                f"[ML] Prediction: {prediction}, confidence: {confidence:.4f}"
            )

            return {
                "prediction": prediction,
                "confidence": round(float(confidence), 4),
                "source": "ml"
            }

        except Exception as e:
            logger.error(f"[ML] Prediction failed: {e}")
            return {
                "prediction": "Unknown",
                "confidence": 0.0,
                "source": "ml",
                "error": str(e)
            }
