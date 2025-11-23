import asyncio
import os
import logging

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from .config import settings
from .db import init_db
from .errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .routers import (
    auth_router,
    dashboard_router,
    deployments_router,
    deployments_runtime_router,
    github_router,
    user_router,
    webhook_router,
    monitoring_router,
    billing_router,
    projects_router,
)
from .routers import auth as auth_module
from .services.monitoring import monitoring_service


logger = logging.getLogger(__name__)

app = FastAPI(title="Autostack API", version="0.1.0")


allowed_origins = settings.frontend_origins or [str(settings.frontend_url)]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.on_event("startup")
async def on_startup() -> None:
    try:
        await init_db()
    except Exception as exc:  # pragma: no cover - defensive startup on Render
        logger.exception("Database initialization failed during startup; continuing without DB: %s", exc)

    # Start background monitoring and health-check loop
    asyncio.create_task(monitoring_service.start_monitoring(interval=60))

    # Start container log streaming for Docker deployments
    if settings.docker_enable:
        from .services.container_log_streamer import start_log_streamer
        start_log_streamer()


# Ensure artifacts directory exists at import time for StaticFiles
os.makedirs(settings.autostack_deploy_dir, exist_ok=True)

# Serve build artifacts
app.mount(
    "/artifacts",
    StaticFiles(directory=settings.autostack_deploy_dir, html=True),
    name="artifacts",
)


# Routers
app.include_router(auth_router)
app.include_router(auth_module.oauth_router)
app.include_router(user_router)
app.include_router(github_router)
app.include_router(deployments_router)
app.include_router(deployments_runtime_router)
app.include_router(dashboard_router)
app.include_router(webhook_router)
app.include_router(monitoring_router)
app.include_router(billing_router)
app.include_router(projects_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "Autostack API", "status": "running", "docs": "/docs"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
