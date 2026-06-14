"""Tests for the ML inference engine."""

import pytest
from backend.ml.inference import MLInference


@pytest.fixture
def ml_engine():
    return MLInference()


class TestMLInference:

    def test_returns_prediction_key(self, ml_engine):
        result = ml_engine.predict("invalid login credentials for admin")
        assert "prediction" in result
        assert "confidence" in result
        assert "source" in result

    def test_source_is_ml(self, ml_engine):
        result = ml_engine.predict("database connection pool exhausted")
        assert result["source"] == "ml"

    def test_confidence_is_between_0_and_1(self, ml_engine):
        result = ml_engine.predict("pod entered crashloopbackoff state")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_classifies_auth_logs(self, ml_engine):
        result = ml_engine.predict("jwt token expired during authentication on auth-service")
        assert result["prediction"] == "Authentication Failure"

    def test_classifies_database_logs(self, ml_engine):
        result = ml_engine.predict("postgres connection timeout on db-cluster")
        assert result["prediction"] == "Database Error"

    def test_classifies_kubernetes_logs(self, ml_engine):
        result = ml_engine.predict("pod entered crashloopbackoff state on k8s-node-4")
        assert result["prediction"] == "Kubernetes CrashLoop"

    def test_high_confidence_on_clear_logs(self, ml_engine):
        result = ml_engine.predict("kafka consumer lag exceeded threshold on kafka-broker")
        assert result["confidence"] >= 0.70

    def test_handles_empty_string(self, ml_engine):
        result = ml_engine.predict("")
        assert "prediction" in result
        assert result["confidence"] >= 0.0
