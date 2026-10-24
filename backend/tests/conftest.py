import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Test-only environment. Must run before any `app` module calls get_settings(),
# so it lives at import time of the root conftest. setdefault lets CI override.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="artef-tests-"))


def _write_test_keys(directory: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_path = directory / "test_private.pem"
    public_path = directory / "test_public.pem"
    private_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    return private_path, public_path


_private_key, _public_key = _write_test_keys(_TEST_DIR)
for _name, _value in {
    "SECRET_KEY": "test-only-secret-key-not-used-anywhere-0123456789",
    "DATABASE_URL": f"sqlite+aiosqlite:///{(_TEST_DIR / 'test.db').as_posix()}",
    "REDIS_URL": "redis://localhost:6379/0",
    "CELERY_BROKER_URL": "memory://",
    "CELERY_RESULT_BACKEND": "cache+memory://",
    "JWT_PRIVATE_KEY_PATH": str(_private_key),
    "JWT_PUBLIC_KEY_PATH": str(_public_key),
    "EVAL_MODE": "local",
    "DEBUG": "false",
    "CELERY_TASK_ALWAYS_EAGER": "true",
    "TARGET_AGENT_BLOCK_PRIVATE_IPS": "false",  # integration tests call a local target agent
}.items():
    os.environ.setdefault(_name, _value)

import pytest  # noqa: E402
from unittest.mock import patch, MagicMock, mock_open  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from uuid import uuid4  # noqa: E402

from app.core.config import Settings  # noqa: E402

# Throwaway keys generated above (no key material is committed to the repository).
PRIVATE_KEY = _private_key.read_text(encoding="utf-8")
PUBLIC_KEY = _public_key.read_text(encoding="utf-8")


def make_test_settings() -> Settings:
    """Build the default settings used across backend tests."""
    return Settings(
        SECRET_KEY='a' * 32,
        # The application only ever creates an async engine, so a sync
        # SQLite URL made every test that touched the database fail with
        # "The asyncio extension requires an async driver".
        DATABASE_URL='sqlite+aiosqlite:///./test.db',
        REDIS_URL='redis://localhost:6379/0',
        CELERY_BROKER_URL='redis://localhost:6379/1',
        CELERY_RESULT_BACKEND='redis://localhost:6379/2',
        ENVIRONMENT='testing',
        DEBUG=False,
        JWT_PRIVATE_KEY_PATH=str(_private_key),
        JWT_PUBLIC_KEY_PATH=str(_public_key),
        EVAL_MODE='local',
        DEV_MOCK_JUDGE=True,
        DEV_MOCK_TARGET_AGENT=True,
        DEV_SEED_DATA=True,
        S3_ACCESS_KEY='test_access_key',
        S3_SECRET_KEY='test_secret_key',
    )


@pytest.fixture
def test_settings():
    """Provide test settings for all tests."""
    return make_test_settings()


@pytest.fixture(autouse=True)
def mock_settings(test_settings):
    """Override settings globally for tests."""
    with patch('app.core.config.get_settings', return_value=test_settings):
        yield


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_access_token():
    """Generate a valid access token for testing."""
    from app.core.security import create_access_token

    # Signed with the throwaway RSA keys generated at the top of this file.
    return create_access_token(
        data={
            "sub": str(uuid4()),
            "username": "test_user",
            "email": "test@example.com",
            "roles": ["admin"],
            "scopes": ["admin", "safety_engineer"],
            "type": "access",
        },
        expires_delta=timedelta(hours=1),
    )


@pytest.fixture
def admin_headers(sample_access_token):
    """Provide authorization headers for admin requests."""
    return {'Authorization': f'Bearer {sample_access_token}'}


@pytest.fixture
def viewer_token():
    """Generate a viewer access token."""
    from app.core.security import create_access_token

    return create_access_token(
        data={
            "sub": str(uuid4()),
            "username": "viewer_user",
            "email": "viewer@example.com",
            "roles": ["viewer"],
            "scopes": ["viewer"],
            "type": "access",
        },
        expires_delta=timedelta(hours=1),
    )


@pytest.fixture
def viewer_headers(viewer_token):
    """Provide authorization headers for viewer requests."""
    return {'Authorization': f'Bearer {viewer_token}'}