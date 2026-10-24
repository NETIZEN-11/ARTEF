from app.core.config import Settings


def test_settings_load(monkeypatch):
    """Test that settings can be instantiated with required fields."""
    # This test checks defaults, so ignore any values set in the environment.
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        S3_ACCESS_KEY="test_key",
        S3_SECRET_KEY="test_secret",
    )
    assert settings.APP_NAME == "Agent Red-Teaming Framework"
    assert settings.SECRET_KEY == "a" * 32
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True


def test_settings_cors_parsing():
    """Test CORS origins parsing."""
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        S3_ACCESS_KEY="test_key",
        S3_SECRET_KEY="test_secret",
        CORS_ORIGINS="http://localhost:3000, http://localhost:8000",
    )
    assert len(settings.cors_origins_list) == 2
    assert "http://localhost:3000" in settings.cors_origins_list
    assert "http://localhost:8000" in settings.cors_origins_list


def test_settings_allowed_hosts_parsing():
    """Test target agent allowed hosts parsing."""
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        S3_ACCESS_KEY="test_key",
        S3_SECRET_KEY="test_secret",
        TARGET_AGENT_ALLOWED_HOSTS="api.example.com, internal.example.com",
    )
    assert len(settings.allowed_hosts_list) == 2
    assert "api.example.com" in settings.allowed_hosts_list
    assert "internal.example.com" in settings.allowed_hosts_list


def test_settings_is_production():
    """Test environment detection with a production-valid configuration."""
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        S3_ACCESS_KEY="test_key",
        S3_SECRET_KEY="test_secret",
        ENVIRONMENT="production",
        CORS_ORIGINS="https://artef.example.com",
        EVAL_MODE="provider",
        DEV_MOCK_JUDGE=False,
        DEV_MOCK_TARGET_AGENT=False,
    )
    assert settings.is_production is True
    assert settings.is_development is False


def test_production_rejects_wildcard_cors():
    """A wildcard CORS origin must be rejected in production."""
    import pytest

    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(
            SECRET_KEY="a" * 32,
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            REDIS_URL="redis://localhost:6379/0",
            CELERY_BROKER_URL="redis://localhost:6379/1",
            CELERY_RESULT_BACKEND="redis://localhost:6379/2",
            S3_ACCESS_KEY="test_key",
            S3_SECRET_KEY="test_secret",
            ENVIRONMENT="production",
            CORS_ORIGINS="*",
            EVAL_MODE="provider",
            DEV_MOCK_JUDGE=False,
            DEV_MOCK_TARGET_AGENT=False,
        )


def test_production_rejects_mock_judges():
    """The deterministic mock judge must never be enabled in production."""
    import pytest

    with pytest.raises(ValueError, match="DEV_MOCK"):
        Settings(
            SECRET_KEY="a" * 32,
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            REDIS_URL="redis://localhost:6379/0",
            CELERY_BROKER_URL="redis://localhost:6379/1",
            CELERY_RESULT_BACKEND="redis://localhost:6379/2",
            S3_ACCESS_KEY="test_key",
            S3_SECRET_KEY="test_secret",
            ENVIRONMENT="production",
            CORS_ORIGINS="https://artef.example.com",
            EVAL_MODE="provider",
            DEV_MOCK_JUDGE=True,
            DEV_MOCK_TARGET_AGENT=False,
        )


def test_production_rejects_local_eval_mode():
    """EVAL_MODE=local uses the mock judge and must be rejected in production."""
    import pytest

    with pytest.raises(ValueError, match="EVAL_MODE"):
        Settings(
            SECRET_KEY="a" * 32,
            DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
            REDIS_URL="redis://localhost:6379/0",
            CELERY_BROKER_URL="redis://localhost:6379/1",
            CELERY_RESULT_BACKEND="redis://localhost:6379/2",
            S3_ACCESS_KEY="test_key",
            S3_SECRET_KEY="test_secret",
            ENVIRONMENT="production",
            CORS_ORIGINS="https://artef.example.com",
            EVAL_MODE="local",
            DEV_MOCK_JUDGE=False,
            DEV_MOCK_TARGET_AGENT=False,
        )


def test_trusted_proxy_ips_are_configurable():
    """The trusted-proxy list must come from configuration, not a constant."""
    settings = Settings(
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
        REDIS_URL="redis://localhost:6379/0",
        CELERY_BROKER_URL="redis://localhost:6379/1",
        CELERY_RESULT_BACKEND="redis://localhost:6379/2",
        S3_ACCESS_KEY="test_key",
        S3_SECRET_KEY="test_secret",
        TRUSTED_PROXY_IPS="10.0.0.1, 10.0.0.2",
    )
    assert settings.TRUSTED_PROXY_IPS == "10.0.0.1, 10.0.0.2"
