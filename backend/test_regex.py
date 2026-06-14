"""Tests for the regex classification engine."""

import pytest
from backend.stages.regex_engine import RegexEngine


@pytest.fixture
def engine():
    return RegexEngine()


class TestRegexMatches:
    """Test that known log patterns are correctly matched by regex rules."""

    def test_auth_failure(self, engine):
        result = engine.classify("authentication failed for admin user")
        assert result["matched"] is True
        assert result["classification"] == "Authentication Failure"
        assert result["source"] == "regex"

    def test_database_timeout(self, engine):
        result = engine.classify("database connection timeout on postgres")
        assert result["matched"] is True
        assert result["classification"] == "Database Error"
        assert result["severity"] == "High"

    def test_api_timeout(self, engine):
        result = engine.classify("gateway request exceeded timeout limit")
        assert result["matched"] is True
        assert result["classification"] == "API Timeout"

    def test_disk_full(self, engine):
        result = engine.classify("filesystem full on prod server")
        assert result["matched"] is True
        assert result["classification"] == "Disk Full"
        assert result["severity"] == "Critical"

    def test_memory_leak(self, engine):
        result = engine.classify("out of memory error on worker node")
        assert result["matched"] is True
        assert result["classification"] == "Memory Leak"
        assert result["severity"] == "Critical"

    def test_ssl_error(self, engine):
        result = engine.classify("ssl certificate expired for api.example.com")
        assert result["matched"] is True
        assert result["classification"] == "SSL Error"

    def test_dns_failure(self, engine):
        result = engine.classify("dns resolution failed for service endpoint")
        assert result["matched"] is True
        assert result["classification"] == "DNS Failure"

    def test_kubernetes_crashloop(self, engine):
        result = engine.classify("pod auth-service in crashloop backoff")
        assert result["matched"] is True
        assert result["classification"] == "Kubernetes CrashLoop"
        assert result["severity"] == "Critical"


class TestRegexNoMatch:
    """Test that unrelated logs are NOT matched by regex."""

    def test_unknown_log(self, engine):
        result = engine.classify("unexpected unknown application crash")
        assert result["matched"] is False

    def test_normal_info_log(self, engine):
        result = engine.classify("user logged in successfully from 192.168.1.1")
        assert result["matched"] is False

    def test_empty_string(self, engine):
        result = engine.classify("")
        assert result["matched"] is False


class TestRegexResultFormat:
    """Test that matched results contain all required fields."""

    def test_result_has_required_fields(self, engine):
        result = engine.classify("authentication failed for admin user")
        assert "matched" in result
        assert "classification" in result
        assert "severity" in result
        assert "solution" in result
        assert "source" in result
