from functools import lru_cache
from typing import List

from pydantic import AnyUrl, EmailStr, Field, computed_field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    secret_key: str = Field(..., alias="SECRET_KEY")
    jwt_access_token_expires_minutes: int = Field(15, alias="JWT_ACCESS_TOKEN_EXPIRES_MINUTES")
    jwt_refresh_token_expires_days: int = Field(7, alias="JWT_REFRESH_TOKEN_EXPIRES_DAYS")

    frontend_url: str | AnyUrl = Field(..., alias="FRONTEND_URL")
    frontend_additional_origins: str | None = Field(None, alias="FRONTEND_ADDITIONAL_ORIGINS")
    backend_url: str | AnyUrl = Field("http://localhost:8000", alias="BACKEND_URL")

    github_client_id: str = Field(..., alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(..., alias="GITHUB_CLIENT_SECRET")
    github_callback_url: str | AnyUrl = Field(..., alias="GITHUB_CALLBACK_URL")
    github_webhook_secret: str = Field(..., alias="GITHUB_WEBHOOK_SECRET")

    google_client_id: str = Field(..., alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., alias="GOOGLE_CLIENT_SECRET")
    google_callback_url: str | AnyUrl = Field(..., alias="GOOGLE_CALLBACK_URL")

    autostack_deploy_dir: str = Field("./deployments", alias="AUTOSTACK_DEPLOY_DIR")
    oauth_state_ttl_seconds: int = Field(300, alias="OAUTH_STATE_TTL_SECONDS")
    build_timeout_seconds: int = Field(1200, alias="BUILD_TIMEOUT_SECONDS")

    jenkins_url: str | AnyUrl | None = Field(None, alias="JENKINS_URL")
    jenkins_user: str | None = Field(None, alias="JENKINS_USER")
    jenkins_api_token: str | None = Field(None, alias="JENKINS_API_TOKEN")
    jenkins_job_name: str | None = Field(None, alias="JENKINS_JOB_NAME")
    jenkins_enable: bool = Field(False, alias="JENKINS_ENABLE")

    docker_enable: bool = Field(False, alias="DOCKER_ENABLE")
    runtime_port_range_start: int = Field(30000, alias="RUNTIME_PORT_RANGE_START")
    runtime_port_range_end: int = Field(39999, alias="RUNTIME_PORT_RANGE_END")
    container_start_timeout: int = Field(600, alias="CONTAINER_START_TIMEOUT")

    kubernetes_enable: bool = Field(False, alias="KUBERNETES_ENABLE")

    smtp_host: str | None = Field(None, alias="SMTP_HOST")
    smtp_port: int | None = Field(None, alias="SMTP_PORT")
    smtp_username: str | None = Field(None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(True, alias="SMTP_USE_TLS")
    email_from: EmailStr | None = Field(None, alias="EMAIL_FROM")

    @computed_field  # type: ignore[misc]
    @property
    def frontend_origins(self) -> List[str]:
        origins: list[str] = []
        base_values = str(self.frontend_url).split(",")
        origins.extend(origin.strip() for origin in base_values if origin.strip())

        if self.frontend_additional_origins:
            extras = [item.strip() for item in self.frontend_additional_origins.split(",") if item.strip()]
            origins.extend(extras)

        seen: set[str] = set()
        unique: list[str] = []
        for origin in origins:
            if origin not in seen:
                unique.append(origin)
                seen.add(origin)
        return unique

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql://", 1)
        if value.startswith("postgresql://") and "+" not in value.split("://", 1)[0]:
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
