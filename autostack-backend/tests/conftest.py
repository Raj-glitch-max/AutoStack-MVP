import asyncio
import os
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_autostack.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["GITHUB_CLIENT_ID"] = "gh-client"
os.environ["GITHUB_CLIENT_SECRET"] = "gh-secret"
os.environ["GITHUB_CALLBACK_URL"] = "http://localhost:8000/auth/github/callback"
os.environ["GITHUB_WEBHOOK_SECRET"] = "webhook-secret"
os.environ["GOOGLE_CLIENT_ID"] = "google-client"
os.environ["GOOGLE_CLIENT_SECRET"] = "google-secret"
os.environ["GOOGLE_CALLBACK_URL"] = "http://localhost:8000/auth/google/callback"
os.environ["AUTOSTACK_DEPLOY_DIR"] = "./test_artifacts"
os.makedirs(os.environ["AUTOSTACK_DEPLOY_DIR"], exist_ok=True)

from app.main import app  # noqa: E402
from app.db import AsyncSessionLocal, Base, engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True, scope="function")
async def _reset_db() -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(autouse=True)
def _mock_enqueue(monkeypatch):
    async def _noop(_: object) -> None:
        return None

    monkeypatch.setattr("app.routers.deployments.enqueue_deployment", _noop)
    monkeypatch.setattr("app.routers.webhook.enqueue_deployment", _noop)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(app=app, base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSessionLocal]:
    async with AsyncSessionLocal() as db:
        yield db

