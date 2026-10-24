"""Fixtures for integration tests: real FastAPI app, real SQLite database, real JWTs.

Nothing here is mocked except the target agent (which tests provide themselves).
"""
import importlib.util
import socket
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def mock_settings():
    """Override the root autouse fixture: integration tests use the real env-based settings."""
    yield


async def _reset_database() -> None:
    from app.core.database import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _create_user(username: str, password: str, role_name: str) -> None:
    from sqlalchemy import select

    from app.core.database import get_session_context
    from app.core.security import get_password_hash
    from app.models.user import Role, User

    async with get_session_context() as session:
        role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
        if role is None:
            role = Role(name=role_name)
            session.add(role)
        user = User(
            email=f"{username}@example.test",
            username=username,
            hashed_password=get_password_hash(password),
        )
        user.roles.append(role)
        session.add(user)


@pytest.fixture
def client(monkeypatch) -> Iterator[TestClient]:
    import importlib

    rate_limit = importlib.import_module("app.core.rate_limit")
    from app.main import app

    # All test requests share one client IP; polling a run must not trip the rate limiter.
    monkeypatch.setattr(rate_limit.settings, "RATE_LIMIT_REQUESTS", 100_000)
    with TestClient(app) as c:
        c.portal.call(_reset_database)
        yield c


@pytest.fixture
def login(client: TestClient) -> Callable[[str], dict[str, str]]:
    """Create a user with the given role, log in through the API, return auth headers."""

    def _login(role: str) -> dict[str, str]:
        username = f"{role}_user"
        password = f"pw-{role}-for-tests"
        client.portal.call(_create_user, username, password, role)
        response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def target_urls():
    """Start the safe and vulnerable demo agents on free ports for this module."""
    spec = importlib.util.spec_from_file_location("demo_target_agent", REPO_ROOT / "demo" / "target_agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    servers, urls = [], {}
    for mode in ("safe", "vulnerable"):
        port = _free_port()
        server = uvicorn.Server(
            uvicorn.Config(module.create_app(mode, "rules"), host="127.0.0.1", port=port, log_level="warning")
        )
        threading.Thread(target=server.run, daemon=True).start()
        servers.append(server)
        urls[mode] = f"http://127.0.0.1:{port}/chat"
    deadline = time.time() + 10
    while not all(s.started for s in servers):
        assert time.time() < deadline, "demo target agents did not start"
        time.sleep(0.05)
    urls["unreachable"] = f"http://127.0.0.1:{_free_port()}/chat"  # nothing listens here
    yield urls
    for server in servers:
        server.should_exit = True
