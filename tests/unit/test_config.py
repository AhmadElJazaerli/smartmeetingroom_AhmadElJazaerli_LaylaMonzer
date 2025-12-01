"""Unit tests for configuration and settings."""
import os

import pytest

from common.config import get_settings, reset_settings_cache


class TestSettings:
    """Test configuration management."""

    def test_get_settings_returns_same_instance(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2

    def test_reset_settings_cache(self):
        """Test that cache can be reset."""
        settings1 = get_settings()
        reset_settings_cache()
        settings2 = get_settings()
        
        # After reset, should be different instances
        assert settings1 is not settings2

    def test_default_database_url(self):
        """Test default database URL."""
        settings = get_settings()
        
        # Should have a database_url set
        assert settings.database_url is not None
        assert isinstance(settings.database_url, str)

    def test_jwt_configuration(self):
        """Test JWT configuration values."""
        settings = get_settings()
        
        assert settings.jwt_secret is not None
        assert settings.jwt_algorithm == "HS256"
        assert settings.access_token_expire_minutes > 0

    def test_rate_limiting_configuration(self):
        """Test rate limiting configuration."""
        settings = get_settings()
        
        assert isinstance(settings.rate_limiting_enabled, bool)
        assert settings.default_rate_limit is not None

    def test_service_ports_configuration(self):
        """Test service port configuration."""
        settings = get_settings()
        
        assert settings.users_service_port == 8001
        assert settings.rooms_service_port == 8002
        assert settings.bookings_service_port == 8003
        assert settings.reviews_service_port == 8004

    def test_cors_origins_configuration(self):
        """Test CORS origins configuration."""
        settings = get_settings()
        
        assert isinstance(settings.cors_origins, list)
        assert len(settings.cors_origins) > 0
