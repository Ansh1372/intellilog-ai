"""Tests for the Regex classification engine."""

import pytest
from backend.stages.regex_engine import RegexEngine


@pytest.fixture
def engine():
    return RegexEngine()


class TestRegexEngine:

    def test_classifies_auth_failure(self, engine):
        result = engine.classify("authentication failed for admin user")
        assert result["matched"] is True
        assert result["classification"] == "Authentication Failure"
        assert result["source"] == "regex"

    def test_classifies_database_error(self, engine):
        result = engine.classify("database connection timeout on postgres")
        assert result["matched"] is True
        assert result["classification"] == "Database Error"
        assert result["severity"] == "High"

    def test_classifies_api_timeout(self, engine):
        result = engine.classify("gateway request exceeded timeout limit")
        assert result["matched"] is True
        assert result["classification"] == "API Timeout"

    def test_classifies_disk_full(self, engine):
        result = engine.classify("filesystem full on production server")
        assert result["matched"] is True
        assert result["classification"] == "Disk Full"
        assert result["severity"] == "Critical"

    def test_classifies_http_500(self, engine):
        result = engine.classify("500 internal server error on api-gateway")
        assert result["matched"] is True
        assert result["classification"] == "HTTP 500"

    def test_classifies_memory_leak(self, engine):
        result = engine.classify("java heap space out of memory")
        assert result["matched"] is True
        assert result["classification"] == "Memory Leak"
        assert result["severity"] == "Critical"

    def test_classifies_ssl_error(self, engine):
        result = engine.classify("ssl certificate expired on prod-server-1")
        assert result["matched"] is True
        assert result["classification"] == "SSL Error"

    def test_returns_no_match_for_unknown_log(self, engine):
        result = engine.classify("some random unknown event happened")
        assert result["matched"] is False
        assert "classification" not in result

    def test_case_insensitive_matching(self, engine):
        result = engine.classify("DATABASE CONNECTION TIMEOUT")
        assert result["matched"] is True
        assert result["classification"] == "Database Error"

    def test_result_contains_solution(self, engine):
        result = engine.classify("authentication login denied")
        assert result["matched"] is True
        assert "solution" in result
        assert len(result["solution"]) > 0
