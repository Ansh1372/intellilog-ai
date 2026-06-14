"""Tests for new features: JSON parsing, search, feedback, rate limiting, alerts."""

import pytest
from backend.utils.json_parser import try_parse_json_log
from backend.middleware.rate_limit import RateLimitState
from backend.alerts.email_alerts import EmailAlertService


class TestJsonParser:
    """Tests for JSON log auto-parsing."""

    def test_parses_json_log_with_msg(self):
        log = '{"level": "error", "msg": "connection timeout", "service": "auth"}'
        message, source = try_parse_json_log(log)
        assert "connection timeout" in message
        assert source == "auth"

    def test_parses_json_log_with_message_field(self):
        log = '{"level": "warn", "message": "disk usage high", "app": "monitor"}'
        message, source = try_parse_json_log(log)
        assert "disk usage high" in message
        assert source == "monitor"

    def test_returns_original_for_non_json(self):
        log = "Jun 14 15:16:01 combo sshd: Failed password for root"
        message, source = try_parse_json_log(log)
        assert message == log
        assert source is None

    def test_returns_original_for_invalid_json(self):
        log = '{"broken json'
        message, source = try_parse_json_log(log)
        assert message == log
        assert source is None

    def test_handles_empty_string(self):
        message, source = try_parse_json_log("")
        assert message == ""
        assert source is None

    def test_includes_level_in_message(self):
        log = '{"level": "error", "msg": "timeout", "source": "api-gw"}'
        message, source = try_parse_json_log(log)
        assert "[ERROR]" in message
        assert "timeout" in message
        assert source == "api-gw"

    def test_no_message_field_returns_original(self):
        log = '{"count": 5, "status": 200}'
        message, source = try_parse_json_log(log)
        assert message == log
        assert source is None


class TestRateLimit:
    """Tests for rate limiting."""

    def test_allows_within_limit(self):
        limiter = RateLimitState(max_per_second=10)
        for _ in range(10):
            assert limiter.is_allowed("test-source") is True

    def test_blocks_over_limit(self):
        limiter = RateLimitState(max_per_second=5)
        for _ in range(5):
            limiter.is_allowed("test-source")
        assert limiter.is_allowed("test-source") is False

    def test_different_sources_independent(self):
        limiter = RateLimitState(max_per_second=2)
        limiter.is_allowed("source-a")
        limiter.is_allowed("source-a")
        # source-a is at limit
        assert limiter.is_allowed("source-a") is False
        # source-b is fine
        assert limiter.is_allowed("source-b") is True

    def test_get_stats(self):
        limiter = RateLimitState(max_per_second=100)
        limiter.is_allowed("postgres")
        limiter.is_allowed("postgres")
        stats = limiter.get_stats()
        assert "postgres" in stats
        assert stats["postgres"]["current_rate"] == 2


class TestEmailAlerts:
    """Tests for email alert service (without actually sending)."""

    def test_disabled_without_credentials(self):
        service = EmailAlertService()
        # No SMTP creds in test env
        assert service.is_available() is False

    def test_should_not_alert_on_low_severity(self):
        service = EmailAlertService()
        service.enabled = True  # Force enable for test
        assert service.should_alert("test", "Auth Failure", "Low") is False
        assert service.should_alert("test", "Auth Failure", "Medium") is False

    def test_should_alert_on_high_severity(self):
        service = EmailAlertService()
        service.enabled = True
        assert service.should_alert("test", "Auth Failure", "High") is True
        assert service.should_alert("test2", "DB Error", "Critical") is True

    def test_deduplication(self):
        service = EmailAlertService()
        service.enabled = True
        # First alert goes through
        assert service.should_alert("postgres", "DB Error", "Critical") is True
        # Same source + classification within 5 min is deduped
        assert service.should_alert("postgres", "DB Error", "Critical") is False
        # Different source is fine
        assert service.should_alert("nginx", "DB Error", "Critical") is True
