import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_default_development_config():
    """Verify development settings load properly."""
    cfg = Settings(ENVIRONMENT="development", DEBUG=True)
    assert cfg.ENVIRONMENT == "development"
    assert cfg.DEBUG is True
    assert cfg.PORT == 8001
    assert cfg.is_production is False
    assert cfg.docs_enabled is True
    assert "https://pdf.electioneasy.in" in cfg.cors_origins_list


def test_production_mode_debug_guardrail():
    """Verify production fails fast if DEBUG is True."""
    with pytest.raises(ValueError, match="SECURITY ALERT: DEBUG must be set to False"):
        Settings(ENVIRONMENT="production", DEBUG=True)


def test_production_mode_default_password_guardrail():
    """Verify production fails fast if default credentials are used in DATABASE_URL."""
    with pytest.raises(ValueError, match="SECURITY ALERT: Default credentials detected in DATABASE_URL"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            DATABASE_URL="postgresql+asyncpg://postgres:postgres@db:5432/voterlens",
        )


def test_production_valid_configuration():
    """Verify valid production settings instantiate without error."""
    cfg = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://app_user:SecureCustomPass99@db:5432/voterlens_prod",
        DATABASE_SYNC_URL="postgresql+psycopg2://app_user:SecureCustomPass99@db:5432/voterlens_prod",
    )
    assert cfg.is_production is True
    assert cfg.docs_enabled is False  # Documentation disabled by default in production
