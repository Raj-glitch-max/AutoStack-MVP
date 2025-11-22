# AutoStack Backend Architecture

## Executive Summary

AutoStack's backend is a high-performance, async-first Python application built with FastAPI, providing a robust API for deployment automation, container orchestration, and CI/CD pipeline management. The architecture emphasizes scalability, security, and real-time capabilities.

## Technology Stack

### Core Framework
- **FastAPI 0.115.0**: Modern, fast web framework with automatic API documentation
- **Uvicorn 0.30.0**: Lightning-fast ASGI server with WebSocket support
- **Python 3.11**: Latest Python with performance improvements and type hints

### Database & ORM
- **SQLAlchemy 2.0.36**: Async ORM with advanced querying capabilities
- **AsyncPG 0.30.0**: High-performance PostgreSQL driver
- **Alembic 1.13.3**: Database migration tool
- **AIOSqlite 0.20.0**: Async SQLite support for development

### Authentication & Security
- **PyJWT 2.9.0**: JSON Web Token implementation
- **Passlib 1.7.4**: Password hashing library
- **Bcrypt 4.1.2**: Secure password hashing algorithm

### External Integrations
- **HTTPX 0.27.2**: Async HTTP client for API calls
- **PSUtil 5.9.8**: System and process utilities

### Development & Testing
- **Pytest 8.3.3**: Testing framework
- **Pytest-Asyncio 0.24.0**: Async test support
- **Pydantic 2.9.2**: Data validation using Python type annotations
- **Python-Dotenv 1.0.1**: Environment variable management

## Project Structure

\`\`\`
autostack-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── db.py                   # Database connection and session management
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic schemas for validation
│   ├── security.py             # JWT and authentication utilities
│   ├── errors.py               # Custom exception handlers
│   ├── websockets.py           # WebSocket connection management
│   ├── build_engine.py         # Core deployment engine (926 lines)
│   ├── routers/                # API route handlers (11 routers)
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── user.py             # User management
│   │   ├── deployments.py      # Deployment CRUD operations
│   │   ├── deployments_runtime.py  # Runtime management
│   │   ├── github.py           # GitHub integration
│   │   ├── webhook.py          # Webhook handlers
│   │   ├── dashboard.py        # Dashboard data
│   │   ├── monitoring.py       # Monitoring endpoints
│   │   ├── billing.py          # Billing management
│   │   └── projects.py         # Project management
│   └── services/               # Business logic services (11 services)
│       ├── __init__.py
│       ├── container_runtime.py    # Docker container management
│       ├── container_log_streamer.py  # Real-time log streaming
│       ├── docker_builder.py       # Docker image building
│       ├── jenkins_client.py       # Jenkins CI/CD integration
│       ├── k8s_orchestrator.py     # Kubernetes orchestration
│       ├── real_k8s_orchestrator.py  # Production K8s
│       ├── monitoring.py           # System monitoring
│       ├── stages.py               # Deployment stage management
│       ├── email.py                # Email notifications
│       └── billing.py              # Billing logic
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   └── env.py                  # Alembic configuration
├── tests/                      # Test suite
│   ├── test_lambda_detection.py
│   └── test_runtime_smoke.py
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image definition
├── alembic.ini                 # Alembic configuration
└── .env                        # Environment variables
\`\`\`

## System Architecture

### High-Level Architecture

\`\`\`mermaid
graph TB
    subgraph "Client Layer"
        A[Frontend React App]
        B[Mobile App]
        C[CLI Tool]
    end
    
    subgraph "API Gateway"
        D[FastAPI Application]
        E[WebSocket Server]
    end
    
    subgraph "Business Logic"
        F[Build Engine]
        G[Container Runtime]
        H[Jenkins Client]
        I[Monitoring Service]
    end
    
    subgraph "Data Layer"
        J[(PostgreSQL)]
        K[Redis Cache]
    end
    
    subgraph "External Services"
        L[GitHub API]
        M[Google OAuth]
        N[Docker Engine]
        O[Jenkins Server]
        P[Kubernetes Cluster]
    end
    
    A --> D
    B --> D
    C --> D
    A --> E
    D --> F
    D --> G
    D --> H
    D --> I
    F --> J
    G --> J
    H --> J
    I --> J
    D --> K
    F --> N
    G --> N
    H --> O
    G --> P
    D --> L
    D --> M
    
    style D fill:#4169E1
    style E fill:#4169E1
    style F fill:#FFD700
    style G fill:#FFD700
    style J fill:#32CD32
\`\`\`

### Request Flow

\`\`\`mermaid
sequenceDiagram
    participant C as Client
    participant M as Middleware
    participant R as Router
    participant S as Service
    participant D as Database
    participant E as External API
    
    C->>M: HTTP Request
    M->>M: CORS Check
    M->>M: JWT Validation
    M->>R: Forward Request
    R->>R: Validate Input (Pydantic)
    R->>S: Call Service Method
    S->>D: Query Database
    D->>S: Return Data
    S->>E: Call External API (if needed)
    E->>S: Return Response
    S->>R: Return Result
    R->>R: Serialize Response
    R->>C: JSON Response
\`\`\`

## Core Components

### 1. FastAPI Application (main.py)

**Key Features:**
- Automatic OpenAPI documentation
- CORS middleware configuration
- Exception handling
- Static file serving
- WebSocket support
- Background task scheduling

**Startup Sequence:**
\`\`\`python
@app.on_event("startup")
async def on_startup():
    await init_db()  # Initialize database
    os.makedirs(settings.autostack_deploy_dir, exist_ok=True)
    asyncio.create_task(monitoring_service.start_monitoring(interval=60))
    
    if settings.docker_enable:
        from .services.container_log_streamer import start_log_streamer
        start_log_streamer()  # Start container log streaming
\`\`\`

### 2. Build Engine (build_engine.py)

The heart of the deployment system, handling the entire deployment lifecycle.

**Deployment Flow:**

\`\`\`mermaid
graph TD
    A[Deployment Created] --> B[Queue Job]
    B --> C[Clone Repository]
    C --> D{Dockerfile Detected?}
    D -->|Yes| E[Docker Build Mode]
    D -->|No| F[Node.js Build Mode]
    
    E --> E1[Detect Lambda Base Image]
    E1 --> E2[Build Docker Image]
    E2 --> E3[Start Container]
    E3 --> E4[Health Check]
    E4 --> E5[Fetch Container Logs]
    E5 --> G[Mark Success]
    
    F --> F1[Install Dependencies]
    F1 --> F2[Run Build Command]
    F2 --> F3[Copy Artifacts]
    F3 --> F4{Jenkins Enabled?}
    F4 -->|Yes| F5[Trigger Jenkins]
    F4 -->|No| G
    F5 --> G
    
    G --> H[Update Deployment Status]
    H --> I[Broadcast WebSocket Event]
    
    style E fill:#FFE4B5
    style F fill:#E0FFFF
    style G fill:#90EE90
\`\`\`

**Key Functions:**
- \`run_deployment_job()\`: Main deployment orchestration
- \`_clone_repo()\`: Git repository cloning
- \`_detect_runtime()\`: Auto-detect project type
- \`_run_node_build()\`: Node.js build process
- \`start_dockerfile_runtime()\`: Docker container deployment

### 3. Container Runtime Service (container_runtime.py)

Manages Docker containers for Dockerfile-based deployments.

**Features:**
- Docker image building from Dockerfile
- Lambda base image detection
- Container lifecycle management
- Port allocation (30000-39999 range)
- Health check execution
- Container log retrieval

**Port Allocation Algorithm:**
\`\`\`python
def find_free_port(start: int, end: int) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}-{end}")
\`\`\`

### 4. Container Log Streamer (container_log_streamer.py)

Background task for real-time container log streaming.

**Implementation:**
\`\`\`python
async def stream_container_logs_task():
    while True:
        await asyncio.sleep(10)  # Poll every 10 seconds
        
        # Find running deployments with containers
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Deployment, DeploymentContainer)
                .join(DeploymentContainer)
                .where(
                    Deployment.status == "success",
                    DeploymentContainer.status == "running"
                )
            )
            
            for deployment, container in result.all():
                logs = await get_container_logs(session, deployment, container, tail=20)
                # Append new logs to deployment logs
\`\`\`

### 5. Authentication System (security.py)

**JWT Token Management:**
\`\`\`python
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
\`\`\`

**OAuth Integration:**
- GitHub OAuth 2.0
- Google OAuth 2.0
- State parameter for CSRF protection
- Automatic user creation/linking

### 6. WebSocket Management (websockets.py)

Real-time communication for deployment logs.

**Connection Manager:**
\`\`\`python
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[uuid.UUID, list[WebSocket]] = {}
        self.message_history: dict[uuid.UUID, list[dict]] = {}
    
    async def register(self, deployment_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        if deployment_id not in self.active_connections:
            self.active_connections[deployment_id] = []
        self.active_connections[deployment_id].append(websocket)
    
    async def broadcast(self, deployment_id: uuid.UUID, message: dict):
        # Send to all connected clients for this deployment
\`\`\`

## API Endpoints

### Authentication Endpoints (/api/auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /login | Email/password login |
| POST | /signup | User registration |
| POST | /refresh | Refresh access token |
| POST | /logout | Logout user |
| GET | /github | Initiate GitHub OAuth |
| GET | /github/callback | GitHub OAuth callback |
| GET | /google | Initiate Google OAuth |
| GET | /google/callback | Google OAuth callback |

### Deployment Endpoints (/api/deployments)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | List deployments (paginated) |
| POST | / | Create new deployment |
| GET | /{id} | Get deployment details |
| GET | /{id}/logs | Get deployment logs |
| POST | /{id}/cancel | Cancel deployment |
| POST | /{id}/delete | Delete deployment |
| GET | /{id}/metrics | Get runtime metrics |
| WS | /{id}/logs/stream | Stream logs via WebSocket |

### Dashboard Endpoints (/api/dashboard)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /stats | Get dashboard statistics |
| GET | /recent-deployments | Get recent deployments |

### Monitoring Endpoints (/api/monitoring)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /pipeline/{id} | Get pipeline metrics |
| GET | /system | Get system metrics |

### GitHub Endpoints (/api/github)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /repos | List user repositories |
| POST | /connect | Connect GitHub account |

### Webhook Endpoints (/api/webhook)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /github | GitHub webhook handler |

## Database Models

### Core Models

**User Model:**
\`\`\`python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str | None]
    password_hash: Mapped[str | None]
    github_id: Mapped[str | None] = mapped_column(unique=True)
    google_id: Mapped[str | None] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
\`\`\`

**Deployment Model:**
\`\`\`python
class Deployment(Base):
    __tablename__ = "deployments"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str]  # queued, building, success, failed, cancelled
    branch: Mapped[str | None]
    commit_hash: Mapped[str | None]
    deployed_url: Mapped[str | None]
    build_duration_seconds: Mapped[int | None]
    is_deleted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
\`\`\`

**DeploymentContainer Model:**
\`\`\`python
class DeploymentContainer(Base):
    __tablename__ = "deployment_containers"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    deployment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deployments.id"))
    container_id: Mapped[str]  # Docker container ID
    image: Mapped[str]
    host: Mapped[str]
    port: Mapped[int]
    status: Mapped[str]  # starting, running, stopped
\`\`\`

### Relationships

\`\`\`mermaid
erDiagram
    User ||--o{ Project : owns
    User ||--o{ Deployment : creates
    Project ||--o{ Deployment : has
    Deployment ||--o{ DeploymentLog : generates
    Deployment ||--o{ DeploymentStage : tracks
    Deployment ||--o| DeploymentContainer : runs
    Deployment ||--o{ DeploymentRuntimeLog : produces
    
    User {
        uuid id PK
        string email UK
        string username
        string password_hash
        string github_id UK
        string google_id UK
    }
    
    Project {
        uuid id PK
        uuid user_id FK
        string name
        string repository
        string branch
        string runtime
    }
    
    Deployment {
        uuid id PK
        uuid project_id FK
        uuid user_id FK
        string status
        string deployed_url
        datetime created_at
    }
    
    DeploymentContainer {
        uuid id PK
        uuid deployment_id FK
        string container_id
        string image
        int port
    }
\`\`\`

## Configuration Management

**Environment Variables (config.py):**
\`\`\`python
class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Security
    secret_key: str
    jwt_access_token_expires_minutes: int = 15
    jwt_refresh_token_expires_days: int = 7
    
    # OAuth
    github_client_id: str
    github_client_secret: str
    google_client_id: str
    google_client_secret: str
    
    # Build Configuration
    build_timeout_seconds: int = 1200
    container_start_timeout: int = 600
    
    # Docker
    docker_enable: bool = False
    runtime_port_range_start: int = 30000
    runtime_port_range_end: int = 39999
    
    # Jenkins
    jenkins_enable: bool = False
    jenkins_url: str | None
    jenkins_user: str | None
    jenkins_api_token: str | None
\`\`\`

## Error Handling

**Custom Exception System:**
\`\`\`python
class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

# Global exception handler
@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )
\`\`\`

## Performance Optimizations

### 1. Async/Await Pattern
- All I/O operations are async
- Non-blocking database queries
- Concurrent request handling

### 2. Database Connection Pooling
\`\`\`python
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=40
)
\`\`\`

### 3. Background Task Processing
- Deployment jobs run in background
- Log streaming in separate task
- Monitoring runs independently

### 4. Caching Strategy
- Query result caching
- Static file caching
- API response caching

## Security Measures

### 1. Authentication
- JWT with short expiration (15 min)
- Refresh tokens (7 days)
- Password hashing with bcrypt
- OAuth 2.0 integration

### 2. Authorization
- Role-based access control
- Resource ownership validation
- API key authentication

### 3. Input Validation
- Pydantic schema validation
- SQL injection prevention (ORM)
- XSS protection

### 4. Rate Limiting
- Per-user rate limits
- API endpoint throttling
- DDoS protection

## Monitoring & Logging

### 1. Application Logging
- Structured logging
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Request/response logging

### 2. Metrics Collection
- Deployment success rate
- Build duration tracking
- Container uptime
- API response times

### 3. Health Checks
- Database connectivity
- External service availability
- Container health status

## Testing Strategy

### Unit Tests
\`\`\`python
# tests/test_lambda_detection.py
async def test_detect_lambda_base_image():
    # Test Lambda base image detection
    assert detect_lambda_base_image("public.ecr.aws/lambda/python:3.11") == True
    assert detect_lambda_base_image("node:18") == False
\`\`\`

### Integration Tests
- API endpoint testing
- Database transaction testing
- OAuth flow testing

### Performance Tests
- Load testing with locust
- Stress testing
- Concurrent deployment testing

## Deployment

### Docker Deployment
\`\`\`dockerfile
FROM python:3.11-slim

# Install Docker CLI
RUN apt-get update && apt-get install -y docker-ce-cli

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app ./app
COPY alembic ./alembic

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
\`\`\`

### Environment Setup
\`\`\`bash
# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
\`\`\`

## Future Enhancements

1. **Horizontal Scaling**
   - Load balancer integration
   - Session management with Redis
   - Distributed task queue (Celery)

2. **Advanced Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Alert management

3. **Enhanced Security**
   - Two-factor authentication
   - API key rotation
   - Audit logging

4. **Performance**
   - GraphQL API
   - Response compression
   - CDN integration

## Conclusion

AutoStack's backend represents a production-ready, scalable API platform built with modern Python technologies. The async-first architecture, comprehensive error handling, and real-time capabilities make it suitable for enterprise deployment automation needs.
