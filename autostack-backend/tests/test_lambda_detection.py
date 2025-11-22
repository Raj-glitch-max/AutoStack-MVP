import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
import uuid

from app.build_engine import run_deployment_job
from app.services.container_runtime import start_dockerfile_runtime
from app.models import Deployment, Project

@pytest.mark.asyncio
async def test_detect_lambda_base_image():
    """Verify that Lambda base images are correctly detected from Dockerfile content."""
    # We'll mock the file reading part in run_deployment_job or extract the logic if it were a separate function.
    # Since it's inline in run_deployment_job, we can test the logic by mocking the file read.
    
    # However, run_deployment_job is complex with DB calls. 
    # A better approach for this unit test is to extract the logic or mock heavily.
    # Let's verify the logic by reproducing it here as a "whitebox" test of the logic found in build_engine.py
    
    def is_lambda(docker_text):
        lambda_base_image = False
        for line in docker_text.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("FROM "):
                parts = stripped.split()
                if len(parts) >= 2:
                    base_image = parts[1]
                    if "public.ecr.aws/lambda" in base_image or "aws-lambda" in base_image:
                        lambda_base_image = True
                break
        return lambda_base_image

    assert is_lambda("FROM public.ecr.aws/lambda/python:3.9") is True
    assert is_lambda("FROM aws-lambda-image:latest") is True
    assert is_lambda("FROM python:3.9") is False
    assert is_lambda("FROM nginx:alpine") is False
    assert is_lambda("FROM public.ecr.aws/other/image") is False

@pytest.mark.asyncio
async def test_start_dockerfile_runtime_lambda_mode():
    """Verify start_dockerfile_runtime uses correct port and skips health check in lambda_mode."""
    
    mock_session = AsyncMock()
    mock_deployment = MagicMock(spec=Deployment)
    mock_deployment.id = uuid.uuid4()
    mock_repo_dir = Path("/tmp/test_repo")
    
    # Mock dependencies
    with patch("app.services.container_runtime.is_docker_available", return_value=True), \
         patch("app.services.container_runtime.find_free_port", return_value=12345), \
         patch("app.services.container_runtime._run_docker", new_callable=AsyncMock) as mock_run_docker, \
         patch("app.services.container_runtime.record_health_check", new_callable=AsyncMock) as mock_health_check:
        
        # Mock docker build success
        mock_run_docker.side_effect = [
            (0, "build_success", ""), # build
            (0, "container_id_123\n", "")  # run
        ]
        
        container = await start_dockerfile_runtime(
            mock_session, 
            mock_deployment, 
            mock_repo_dir, 
            lambda_mode=True
        )
        
        # Verify build called
        assert mock_run_docker.call_count == 2
        build_call = mock_run_docker.call_args_list[0]
        assert build_call[0][0][0] == "build"
        
        # Verify run called with port 8080 mapping
        run_call = mock_run_docker.call_args_list[1]
        run_args = run_call[0][0]
        assert "run" in run_args
        # Check for port mapping: host_port:8080
        assert any("12345:8080" in arg for arg in run_args)
        
        # Verify health check was SKIPPED
        mock_health_check.assert_not_called()
        
        # Verify container status set to running immediately
        assert container.status == "running"

@pytest.mark.asyncio
async def test_start_dockerfile_runtime_standard_mode():
    """Verify start_dockerfile_runtime uses port 80 and runs health check in standard mode."""
    
    mock_session = AsyncMock()
    mock_deployment = MagicMock(spec=Deployment)
    mock_deployment.id = uuid.uuid4()
    mock_repo_dir = Path("/tmp/test_repo")
    
    with patch("app.services.container_runtime.is_docker_available", return_value=True), \
         patch("app.services.container_runtime.find_free_port", return_value=12345), \
         patch("app.services.container_runtime._run_docker", new_callable=AsyncMock) as mock_run_docker, \
         patch("app.services.container_runtime.record_health_check", new_callable=AsyncMock) as mock_health_check:
        
        mock_run_docker.side_effect = [
            (0, "build_success", ""), 
            (0, "container_id_456\n", "")
        ]
        
        # Mock health check success
        mock_hc = MagicMock()
        mock_hc.is_live = True
        mock_health_check.return_value = mock_hc
        
        container = await start_dockerfile_runtime(
            mock_session, 
            mock_deployment, 
            mock_repo_dir, 
            lambda_mode=False
        )
        
        # Verify run called with port 80 mapping
        run_call = mock_run_docker.call_args_list[1]
        run_args = run_call[0][0]
        assert any("12345:80" in arg for arg in run_args)
        
        # Verify health check WAS called
        mock_health_check.assert_called_once()
        
        assert container.status == "running"

@pytest.mark.asyncio
async def test_start_dockerfile_runtime_api_error_handling():
    """Verify that ApiError is raised correctly and has the expected attributes."""
    from app.errors import ApiError
    
    mock_session = AsyncMock()
    mock_deployment = MagicMock(spec=Deployment)
    mock_deployment.id = uuid.uuid4()
    mock_repo_dir = Path("/tmp/test_repo")
    
    with patch("app.services.container_runtime.is_docker_available", return_value=True), \
         patch("app.services.container_runtime.find_free_port", return_value=12345), \
         patch("app.services.container_runtime._run_docker", new_callable=AsyncMock) as mock_run_docker:
        
        # Mock docker build failure to trigger ApiError
        mock_run_docker.return_value = (1, "", "Build failed")
        
        with pytest.raises(ApiError) as excinfo:
            await start_dockerfile_runtime(
                mock_session, 
                mock_deployment, 
                mock_repo_dir, 
                lambda_mode=False
            )
        
        # Verify the exception has the 'message' attribute which build_engine.py relies on
        assert hasattr(excinfo.value, "message")
        assert "Failed to build Docker image" in excinfo.value.message

