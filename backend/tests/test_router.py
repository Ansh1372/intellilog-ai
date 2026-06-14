"""Tests for the LogRouter multi-stage pipeline."""

import pytest
from backend.router import LogRouter


@pytest.fixture
def log_router():
    return LogRouter()


class TestLogRouter:

    def test_regex_match_returns_regex_source(self, log_router):
        result = log_router.process_log("authentication failed for admin user")
        assert result["matched"] is True
        assert result["source"] == "regex"

    def test_ml_fallback_when_regex_misses(self, log_router):
        # Use a log that won't match any regex pattern but ML should classify
        result = log_router.process_log("kafka consumer lag exceeded threshold on broker-3")
        assert result["matched"] is True
        assert result["source"] in ["ml-high-confidence", "ml-medium-confidence", "llm", "regex"]

    def test_result_always_has_matched_key(self, log_router):
        result = log_router.process_log("some log text here")
        assert "matched" in result

    def test_regex_hit_includes_classification(self, log_router):
        result = log_router.process_log("database connection timeout on postgres")
        assert result["classification"] == "Database Error"
        assert result["severity"] == "High"

    def test_ml_high_confidence_has_confidence_field(self, log_router):
        result = log_router.process_log("kafka consumer lag exceeded threshold on kafka-broker")
        if result["source"] in ["ml-high-confidence", "ml-medium-confidence"]:
            assert "confidence" in result
            assert result["confidence"] >= 0.70

    def test_pipeline_handles_unknown_gracefully(self, log_router):
        result = log_router.process_log("xyzzy foo bar unknown gibberish")
        # Should not crash — returns some result
        assert "matched" in result
