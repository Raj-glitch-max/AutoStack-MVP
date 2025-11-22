from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class APIModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ErrorDetails(APIModel):
    code: str
    message: str
    status_code: int
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(APIModel):
    error: ErrorDetails


class SignupRequest(APIModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(APIModel):
    email: EmailStr
    password: str


class RefreshRequest(APIModel):
    refresh_token: str


class LogoutRequest(APIModel):
    refresh_token: str


class UserInfo(APIModel):
    id: str
    name: str
    email: EmailStr
    avatar_url: Optional[str] = None


class AuthTokens(APIModel):
    access_token: str
    refresh_token: str


class AuthResponse(AuthTokens):
    user: UserInfo


class SessionResponse(APIModel):
    user: UserInfo
    authenticated: bool = True


class UserProfile(APIModel):
    id: str
    name: str
    email: EmailStr
    avatar_url: Optional[str] = None


class UserProfileUpdate(APIModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserPreferences(APIModel):
    theme: str = "system"
    email_notifications: bool = True
    deployment_success_notifications: bool = True
    deployment_failure_notifications: bool = True


class GithubConnectionStatus(APIModel):
    connected: bool
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    scope: Optional[str] = None
    connected_at: Optional[datetime] = None


class GithubRepo(APIModel):
    id: int
    name: str
    full_name: str
    private: bool
    default_branch: str


class GithubReposResponse(APIModel):
    repos: List[GithubRepo]


class GithubBranch(APIModel):
    name: str


class GithubBranchesResponse(APIModel):
    branches: List[GithubBranch]


class DockerfileDetectionResponse(APIModel):
    has_dockerfile: bool
    path: Optional[str] = None


class DeploymentCreateRequest(APIModel):
    repository: str
    branch: str = "main"
    build_command: str = "npm run build"
    output_dir: str = "dist"
    env_vars: Optional[str] = None
    auto_deploy_enabled: Optional[bool] = None
    auto_deploy_branch: Optional[str] = None
    runtime: Optional[str] = None


class DeploymentItem(APIModel):
    id: str
    name: str
    project_id: Optional[str] = None
    repo: Optional[str] = None
    branch: str
    status: str
    commit: Optional[str] = None
    commit_message: Optional[str] = None
    author: Optional[str] = None
    duration: Optional[str] = None
    time: str
    timestamp: Optional[datetime] = None
    url: Optional[str] = None
    creator_type: str = "manual"
    is_production: bool = False
    failed_reason: Optional[str] = None


class Pagination(APIModel):
    current_page: int
    total_pages: int
    total_items: int


class DeploymentListResponse(APIModel):
    deployments: List[DeploymentItem]
    pagination: Pagination


class RecentDeploymentItem(DeploymentItem):
    pass


class RecentDeploymentsResponse(APIModel):
    recent_deployments: List[RecentDeploymentItem]


class DeploymentStageModel(APIModel):
    name: str
    status: str
    timestamp: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CommitInfo(APIModel):
    sha: Optional[str] = None
    message: Optional[str] = None
    author: Optional[str] = None
    timestamp: Optional[datetime] = None


class DeploymentDetailResponse(APIModel):
    id: str
    project_id: Optional[str] = None
    name: str
    repo: Optional[str] = None
    branch: str
    status: str
    time: str
    url: Optional[str] = None
    commit: Optional[CommitInfo] = None
    duration: Optional[str] = None
    creator_type: str
    is_production: bool
    env_vars: Optional[str] = None
    stages: List[DeploymentStageModel]
    logs: List[str]
    failed_reason: Optional[str] = None


class DeploymentLogsResponse(APIModel):
    logs: List[str]


class DashboardStats(APIModel):
    total_deployments: int
    weekly_change: str
    active_projects: int
    today_deployments: int
    success_rate: float
    monthly_success_change: float
    avg_deploy_time: str
    time_improvement: str


class DashboardStatsResponse(APIModel):
    stats: DashboardStats
    recent_deployments: List[RecentDeploymentItem]


class BillingProjectBreakdown(APIModel):
    project_id: str
    name: str
    total_deployments: int
    successful_deployments: int
    pipeline_minutes: float
    estimated_cost: float


class BillingSummary(APIModel):
    currency: str
    total_month_to_date: float
    projected_monthly: float
    last_updated: datetime
    projects: List[BillingProjectBreakdown]


class BillingSummaryResponse(APIModel):
    billing: BillingSummary


class ForgotPasswordRequest(APIModel):
    email: EmailStr


class ResetPasswordRequest(APIModel):
    token: str
    password: str = Field(min_length=8)


class MessageResponse(APIModel):
    success: bool = True


class ProjectSettingsUpdate(APIModel):
    auto_deploy_enabled: Optional[bool] = None
    auto_deploy_branch: Optional[str] = None


class ProjectSummary(APIModel):
    id: str
    name: str
    repository: str
    branch: str
    runtime: str
    auto_deploy_enabled: bool
    auto_deploy_branch: Optional[str] = None


class ProjectAnalytics(APIModel):
    deployments_count: int
    success_count: int
    failure_count: int
    last_5_durations: list[float]
    avg_build_time: Optional[float] = None
    uptime_last_24h: Optional[float] = None


class ProjectAnalyticsResponse(APIModel):
    analytics: ProjectAnalytics
