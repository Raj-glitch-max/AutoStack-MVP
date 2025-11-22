import os
import uuid

import pytest

from httpx import AsyncClient

from app.main import app


pytestmark = pytest.mark.smoke


@pytest.mark.asyncio
async def test_runtime_smoke_docker_flag_only():
    # This is a lightweight placeholder smoke test to ensure the runtime endpoints are wired.
    # It does NOT start Docker; full integration tests should be run in an environment with Docker available.
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
