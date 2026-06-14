"""Tests for the ML inference engine."""

import pytest
from backend.ml.inference import MLInference


@pytest.fixture
def ml_engine():
    return MLInference()


KNOWN_LABELS = [
    "Authentication Failure", "Database Error", "API Timeout",
    "Disk Full", "HTTP 403", "HTTP 404", "HTTP 500",
    "Memory Leak", "CPU Spike", "Kubernetes CrashLoop",
    "SSL Error", "DNS Failure", "Redis Failure",
    "Kafka Failure", "Payment Failure",
]


class TestMLPredictionFormat:
    """Test that ML predictions return the expected structure."""

    def test_returns_prediction_key(self, ml_engine):
        result = ml_engine.predict("database connection timeout")
        assert "prediction" in result
        assert "confidence" in result
        assert "source" in result

    def test_confidence_between_0_and_1(self, ml_engine):
        result = ml_engine.predict("authentication failed for admin")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_source_is_ml(self, ml_engine):
        result = ml_engine.predict("disk storage exceeded on server")
        assert result["source"] == "ml"


class TestMLPredictionAccuracy:
    """Test that ML correctly classifies clear-cut log patterns."""

    def test_auth_failure(self, ml_engine):
        result = ml_engine.predict("invalid login credentials for admin")
        assert result["prediction"] == "Authentication Failure"
        assert result["confidence"] > 0.5

    def test_database_error(self, ml_engine):
        result = ml_engine.predict("postgres database connection timeout")
        assert result["prediction"] == "Database Error"

    def test_disk_full(self, ml_engine):
        result = ml_engine.predict("disk storage exceeded on production server")
        assert result["prediction"] == "Disk Full"

    def test_prediction_is_known_label(self, ml_engine):
        result = ml_engine.predict("gateway request exceeded timeout limit")
        assert result["prediction"] in KNOWN_LABELS


class TestMLEdgeCases:
    """Test ML behavior on unusual inputs."""

    def test_ambiguous_log_has_lower_confidence(self, ml_engine):
        result = ml_engine.predict("strange unknown distributed system failure")
        # Ambiguous logs should have lower confidence than clear ones
        clear_result = ml_engine.predict("authentication failed for admin")
        assert result["confidence"] <= clear_result["confidence"]

    def test_empty_string_does_not_crash(self, ml_engine):
        result = ml_engine.predict("")
        assert "prediction" in result
