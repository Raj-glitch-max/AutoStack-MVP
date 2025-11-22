import hmac
import json
import secrets
import uuid
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Deployment, DeploymentLog, DeploymentStage, Project, User
from app.security import create_access_token
from app.main import app


pytestmark = pytest.mark.asyncio


async def _signup_user(client, email="test@example.com", password="Passw0rd!"):
    payload = {"name": "Test User", "email": email, "password": password}
    response = await client.post("/api/auth/signup", json=payload)
    assert response.status_code == 200
    return response.json()


@pytest.mark.smoke
async def test_auth_signup_and_login(client):
    payload = {"name": "Smoke User", "email": "smoke@example.com", "password": "Passw0rd!"}
    signup = await client.post("/api/auth/signup", json=payload)
    assert signup.status_code == 200

    login = await client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 200
    data = login.json()
    assert "accessToken" in data
    assert data["user"]["email"] == payload["email"]


@pytest.mark.smoke
async def test_manual_deployment_creation_records_stage(client, session: AsyncSessionLocal):
    auth = await _signup_user(client, email="deploy@example.com")
    token = auth["accessToken"]

    payload = {
        "repository": "octocat/Hello-World",
        "branch": "main",
        "buildCommand": "npm run build",
        "outputDir": "dist",
    }
    response = await client.post(
        "/api/deployments",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    deployment_uuid = uuid.UUID(data["id"])
    deployment = await session.get(Deployment, deployment_uuid)
    assert deployment is not None

    stages = await session.execute(
        select(DeploymentStage.stage_name, DeploymentStage.status).where(DeploymentStage.deployment_id == deployment_uuid)
    )
    stage_rows = stages.all()
    assert any(row.stage_name == "Queued" for row in stage_rows)


@pytest.mark.smoke
async def test_github_webhook_signature(client, session: AsyncSessionLocal):
    user = User(name="Repo Owner", email="repo@example.com")
    session.add(user)
    await session.flush()

    project = Project(
        user_id=user.id,
        name="Hello",
        repository="octocat/Hello-World",
        auto_deploy_enabled=True,
        auto_deploy_branch="main",
    )
    session.add(project)
    await session.commit()

    payload = {
        "ref": "refs/heads/main",
        "repository": {"full_name": project.repository},
        "head_commit": {
            "id": secrets.token_hex(20),
            "message": "Test commit",
            "author": {"name": "CI"},
        },
    }
    body = json.dumps(payload).encode()
    secret = "webhook-secret"
    signature = "sha256=" + hmac.new(secret.encode(), body, sha256).hexdigest()

    response = await client.post(
        "/webhook/github",
        content=body,
        headers={
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "push",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"

    deployment_id = uuid.UUID(data["deploymentId"])
    deployment = await session.get(Deployment, deployment_id)
    assert deployment is not None


@pytest.mark.smoke
async def test_websocket_log_history(session: AsyncSessionLocal):
    user = User(name="Websocket User", email="ws@example.com")
    session.add(user)
    await session.flush()

    project = Project(
        user_id=user.id,
        name="WS Project",
        repository="octocat/ws",
    )
    session.add(project)
    await session.flush()

    deployment = Deployment(project_id=project.id, user_id=user.id, status="queued")
    session.add(deployment)
    await session.flush()

    for idx in range(2):
        session.add(DeploymentLog(deployment_id=deployment.id, message=f"log-{idx}"))
    await session.commit()

    token = create_access_token(user)
    client = TestClient(app)
    with client.websocket_connect(f"/api/deployments/{deployment.id}/logs/stream?token={token}") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "history"
        assert message["logs"] == ["log-0", "log-1"]

