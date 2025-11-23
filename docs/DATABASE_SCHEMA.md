# AutoStack Database Schema Documentation

## Executive Summary

AutoStack uses PostgreSQL as its primary database, leveraging SQLAlchemy 2.0's async ORM capabilities for high-performance data operations. The schema is designed for scalability, data integrity, and efficient querying, supporting the full deployment lifecycle from user authentication to container orchestration.

## Database Technology

### Core Technologies
- **PostgreSQL 14+**: Production-grade relational database
- **SQLAlchemy 2.0.36**: Modern async ORM with type hints
- **AsyncPG 0.30.0**: High-performance PostgreSQL driver
- **Alembic 1.13.3**: Database migration management

### Key Features
- **Async Operations**: All database queries are non-blocking
- **Type Safety**: Full type hints with Mapped[] annotations
- **Cascade Deletes**: Automatic cleanup of related records
- **Soft Deletes**: Deployments marked as deleted, not removed
- **Indexes**: Optimized for common query patterns
- **UUID Primary Keys**: Distributed-friendly identifiers

## Entity Relationship Diagram

\`\`\`mermaid
erDiagram
    User ||--o{ Project : "owns"
    User ||--o{ Deployment : "creates"
    User ||--o| UserPreferences : "has"
    User ||--o| GithubConnection : "has"
    User ||--o{ Session : "has"
    User ||--o{ PasswordResetToken : "has"
    
    Project ||--o{ Deployment : "contains"
    
    Deployment ||--o{ DeploymentLog : "generates"
    Deployment ||--o{ DeploymentStage : "tracks"
    Deployment ||--o| DeploymentContainer : "runs"
    Deployment ||--o{ DeploymentHealthCheck : "monitors"
    Deployment ||--o{ DeploymentRuntimeLog : "produces"
    Deployment ||--o{ WebhookPayload : "triggers"
    
    User {
        UUID id PK
        string name
        string email UK
        string password_hash
        string avatar_url
        string github_id UK
        string google_id UK
        boolean email_verified
        datetime created_at
        datetime updated_at
    }
    
    Project {
        UUID id PK
        UUID user_id FK
        string name
        string repository
        string branch
        string build_command
        string output_dir
        string env_vars
        string runtime
        boolean auto_deploy_enabled
        string auto_deploy_branch
        datetime created_at
        datetime updated_at
    }
    
    Deployment {
        UUID id PK
        UUID project_id FK
        UUID user_id FK
        string status
        string branch
        string commit_hash
        string commit_message
        string author
        datetime commit_timestamp
        string creator_type
        boolean is_production
        string env_vars
        integer build_duration_seconds
        string failed_reason
        string deployed_url
        datetime started_at
        datetime completed_at
        datetime created_at
        boolean is_deleted
    }
    
    DeploymentContainer {
        UUID id PK
        UUID deployment_id FK
        string container_id
        string image
        string host
        integer port
        string status
        datetime created_at
        datetime stopped_at
    }
    
    DeploymentLog {
        UUID id PK
        UUID deployment_id FK
        datetime timestamp
        string log_level
        string message
        datetime created_at
    }
    
    DeploymentStage {
        UUID id PK
        UUID deployment_id FK
        string stage_name
        string status
        datetime started_at
        datetime completed_at
        string error_message
        datetime created_at
    }
\`\`\`

## Database Tables

### 1. Users Table

**Purpose**: Store user account information and authentication credentials.

**Schema:**
\`\`\`sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    avatar_url TEXT,
    github_id VARCHAR(255) UNIQUE,
    google_id VARCHAR(255) UNIQUE,
    email_verified BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_github_id ON users(github_id);
CREATE INDEX idx_users_google_id ON users(google_id);
\`\`\`

**Key Fields:**
- \`id\`: UUID primary key
- \`email\`: Unique email address (indexed)
- \`password_hash\`: Bcrypt hashed password (nullable for OAuth users)
- \`github_id\`: GitHub OAuth identifier
- \`google_id\`: Google OAuth identifier
- \`email_verified\`: Email verification status

**Relationships:**
- One-to-Many with Projects
- One-to-Many with Deployments
- One-to-One with UserPreferences
- One-to-One with GithubConnection
- One-to-Many with Sessions
- One-to-Many with PasswordResetTokens

### 2. Projects Table

**Purpose**: Store project configuration and deployment settings.

**Schema:**
\`\`\`sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    repository VARCHAR(255) NOT NULL,
    branch VARCHAR(100) DEFAULT 'main' NOT NULL,
    build_command TEXT DEFAULT 'npm run build' NOT NULL,
    output_dir VARCHAR(255) DEFAULT 'dist' NOT NULL,
    env_vars TEXT,
    github_repo_id VARCHAR(255),
    runtime VARCHAR(50) DEFAULT 'static' NOT NULL,
    auto_deploy_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    auto_deploy_branch VARCHAR(100),
    jenkins_job_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
\`\`\`

**Key Fields:**
- \`repository\`: Git repository URL
- \`branch\`: Default branch for deployments
- \`build_command\`: Command to build the project
- \`output_dir\`: Directory containing build artifacts
- \`runtime\`: Deployment runtime (static, docker, nodejs)
- \`auto_deploy_enabled\`: Enable automatic deployments
- \`auto_deploy_branch\`: Branch to auto-deploy

**Relationships:**
- Many-to-One with User
- One-to-Many with Deployments

### 3. Deployments Table

**Purpose**: Track individual deployment instances and their lifecycle.

**Schema:**
\`\`\`sql
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'queued',
    branch VARCHAR(100),
    commit_hash VARCHAR(40),
    commit_message TEXT,
    author VARCHAR(255),
    commit_timestamp TIMESTAMP,
    creator_type VARCHAR(20) DEFAULT 'manual' NOT NULL,
    is_production BOOLEAN DEFAULT FALSE NOT NULL,
    env_vars TEXT,
    build_duration_seconds INTEGER,
    failed_reason TEXT,
    deployed_url TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL
);

CREATE INDEX idx_deployments_project_id ON deployments(project_id);
CREATE INDEX idx_deployments_user_id ON deployments(user_id);
CREATE INDEX idx_deployments_status ON deployments(status);
CREATE INDEX idx_deployments_created_at ON deployments(created_at DESC);
\`\`\`

**Status Values:**
- \`queued\`: Waiting to start
- \`cloning\`: Cloning repository
- \`checkout\`: Checking out branch
- \`installing\`: Installing dependencies
- \`building\`: Running build
- \`copying\`: Copying artifacts
- \`success\`: Deployment successful
- \`failed\`: Deployment failed
- \`cancelled\`: Deployment cancelled

**Key Fields:**
- \`status\`: Current deployment status (indexed)
- \`commit_hash\`: Git commit SHA
- \`creator_type\`: manual, webhook, or scheduled
- \`is_production\`: Production deployment flag
- \`build_duration_seconds\`: Total build time
- \`deployed_url\`: URL where deployment is accessible
- \`is_deleted\`: Soft delete flag

**Relationships:**
- Many-to-One with Project
- Many-to-One with User
- One-to-Many with DeploymentLogs
- One-to-Many with DeploymentStages
- One-to-One with DeploymentContainer
- One-to-Many with DeploymentHealthChecks
- One-to-Many with DeploymentRuntimeLogs

### 4. Deployment Logs Table

**Purpose**: Store build and deployment log messages.

**Schema:**
\`\`\`sql
CREATE TABLE deployment_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT NOW(),
    log_level VARCHAR(20),
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deployment_logs_deployment_id ON deployment_logs(deployment_id);
CREATE INDEX idx_deployment_logs_timestamp ON deployment_logs(timestamp);
\`\`\`

**Log Levels:**
- \`info\`: Informational messages
- \`warning\`: Warning messages
- \`error\`: Error messages
- \`debug\`: Debug messages

**Usage:**
- Real-time log streaming via WebSocket
- Historical log viewing
- Debugging failed deployments

### 5. Deployment Stages Table

**Purpose**: Track individual stages of the deployment pipeline.

**Schema:**
\`\`\`sql
CREATE TABLE deployment_stages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    stage_name VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deployment_stages_deployment_id ON deployment_stages(deployment_id);
\`\`\`

**Stage Names:**
- \`queued\`: Initial queue stage
- \`cloning\`: Repository cloning
- \`checkout\`: Branch checkout
- \`installing\`: Dependency installation
- \`building\`: Build execution
- \`copying\`: Artifact copying
- \`deploying\`: Deployment to runtime

**Status Values:**
- \`pending\`: Not started
- \`in_progress\`: Currently running
- \`completed\`: Successfully completed
- \`failed\`: Failed with error
- \`cancelled\`: Cancelled by user

### 6. Deployment Containers Table

**Purpose**: Track Docker containers for Dockerfile-based deployments.

**Schema:**
\`\`\`sql
CREATE TABLE deployment_containers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    container_id VARCHAR(255) NOT NULL,
    image VARCHAR(255) NOT NULL,
    host VARCHAR(255) DEFAULT 'localhost' NOT NULL,
    port INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'starting' NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    stopped_at TIMESTAMP
);

CREATE INDEX idx_deployment_containers_deployment_id ON deployment_containers(deployment_id);
CREATE INDEX idx_deployment_containers_status ON deployment_containers(status);
\`\`\`

**Key Fields:**
- \`container_id\`: Docker container ID
- \`image\`: Docker image name
- \`port\`: Exposed port (30000-39999 range)
- \`status\`: starting, running, stopped

**Container Lifecycle:**
1. Container created → status: \`starting\`
2. Container running → status: \`running\`
3. Container stopped → status: \`stopped\`, \`stopped_at\` set

### 7. Deployment Health Checks Table

**Purpose**: Store health check results for deployed containers.

**Schema:**
\`\`\`sql
CREATE TABLE deployment_health_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    http_status INTEGER,
    latency_ms INTEGER,
    is_live BOOLEAN DEFAULT FALSE NOT NULL,
    checked_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deployment_health_checks_deployment_id ON deployment_health_checks(deployment_id);
\`\`\`

**Usage:**
- Monitor container health
- Track uptime and latency
- Alert on failures

### 8. Deployment Runtime Logs Table

**Purpose**: Store container runtime logs (Docker logs).

**Schema:**
\`\`\`sql
CREATE TABLE deployment_runtime_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    source VARCHAR(50) DEFAULT 'docker' NOT NULL,
    log_level VARCHAR(20),
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deployment_runtime_logs_deployment_id ON deployment_runtime_logs(deployment_id);
\`\`\`

**Sources:**
- \`docker\`: Docker container logs
- \`k8s\`: Kubernetes pod logs
- \`system\`: System-level logs

### 9. User Preferences Table

**Purpose**: Store user-specific settings and preferences.

**Schema:**
\`\`\`sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'system',
    email_notifications BOOLEAN DEFAULT TRUE,
    deployment_success_notifications BOOLEAN DEFAULT TRUE,
    deployment_failure_notifications BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
\`\`\`

**Theme Options:**
- \`light\`: Light theme
- \`dark\`: Dark theme
- \`system\`: Follow system preference

### 10. GitHub Connection Table

**Purpose**: Store GitHub OAuth tokens and connection details.

**Schema:**
\`\`\`sql
CREATE TABLE github_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    github_username VARCHAR(255),
    github_access_token TEXT NOT NULL,
    github_refresh_token TEXT,
    token_expires_at TIMESTAMP,
    scope TEXT,
    connected_at TIMESTAMP DEFAULT NOW()
);
\`\`\`

**Security:**
- Tokens stored encrypted
- Automatic token refresh
- Scope validation

### 11. Sessions Table

**Purpose**: Track user sessions for refresh token rotation.

**Schema:**
\`\`\`sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
\`\`\`

**Session Management:**
- 7-day expiration by default
- Automatic cleanup of expired sessions
- Token rotation on refresh

### 12. Password Reset Tokens Table

**Purpose**: Manage password reset tokens.

**Schema:**
\`\`\`sql
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
\`\`\`

**Security:**
- Tokens hashed before storage
- 1-hour expiration
- Single-use tokens

### 13. Webhook Payloads Table

**Purpose**: Store incoming webhook payloads for audit and debugging.

**Schema:**
\`\`\`sql
CREATE TABLE webhook_payloads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deployment_id UUID REFERENCES deployments(id) ON DELETE SET NULL,
    provider VARCHAR(50) NOT NULL,
    payload_json JSONB NOT NULL,
    headers JSONB NOT NULL,
    received_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_webhook_payloads_deployment_id ON webhook_payloads(deployment_id);
CREATE INDEX idx_webhook_payloads_provider ON webhook_payloads(provider);
\`\`\`

**Providers:**
- \`github\`: GitHub webhooks
- \`gitlab\`: GitLab webhooks
- \`bitbucket\`: Bitbucket webhooks

## Database Migrations

### Migration Management with Alembic

**Migration Files:**
1. \`7922132ebbdd_initial_schema.py\`: Initial database schema
2. \`a1b2c3d4e5f6_runtime_models.py\`: Runtime and container models

**Running Migrations:**
\`\`\`bash
# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Generate new migration
alembic revision --autogenerate -m "description"
\`\`\`

## Query Patterns & Optimization

### Common Queries

**1. Get User's Recent Deployments:**
\`\`\`python
query = (
    select(Deployment, Project)
    .join(Project, Deployment.project_id == Project.id)
    .where(
        Deployment.user_id == user_id,
        Deployment.is_deleted.is_(False)
    )
    .order_by(Deployment.created_at.desc())
    .limit(10)
)
\`\`\`

**2. Get Deployment with All Related Data:**
\`\`\`python
deployment = await session.get(
    Deployment,
    deployment_id,
    options=[
        selectinload(Deployment.logs),
        selectinload(Deployment.stages),
        selectinload(Deployment.containers),
        selectinload(Deployment.health_checks)
    ]
)
\`\`\`

**3. Get Running Containers:**
\`\`\`python
query = (
    select(Deployment, DeploymentContainer)
    .join(DeploymentContainer)
    .where(
        Deployment.status == "success",
        DeploymentContainer.status == "running"
    )
)
\`\`\`

### Index Strategy

**Indexed Columns:**
- \`users.email\`: Unique login lookup
- \`deployments.project_id\`: Project deployments
- \`deployments.user_id\`: User deployments
- \`deployments.status\`: Status filtering
- \`deployments.created_at\`: Time-based queries
- \`deployment_logs.deployment_id\`: Log retrieval
- \`deployment_logs.timestamp\`: Time-ordered logs

## Data Integrity

### Foreign Key Constraints

**Cascade Deletes:**
- Deleting a User cascades to Projects, Deployments, Sessions
- Deleting a Project cascades to Deployments
- Deleting a Deployment cascades to Logs, Stages, Containers

**Set NULL:**
- Deleting a Deployment sets \`webhook_payloads.deployment_id\` to NULL

### Soft Deletes

**Deployments:**
- \`is_deleted\` flag prevents physical deletion
- Allows data retention for analytics
- Excluded from user-facing queries

## Performance Considerations

### Connection Pooling
\`\`\`python
engine = create_async_engine(
    database_url,
    pool_size=20,        # Base pool size
    max_overflow=40,     # Additional connections
    pool_pre_ping=True   # Verify connections
)
\`\`\`

### Query Optimization
- Use \`selectinload()\` for eager loading
- Limit result sets with pagination
- Index frequently queried columns
- Use \`exists()\` for existence checks

### Monitoring
- Track slow queries (> 1 second)
- Monitor connection pool usage
- Alert on deadlocks
- Track table sizes

## Backup & Recovery

### Backup Strategy
- Daily full backups
- Continuous WAL archiving
- Point-in-time recovery capability
- 30-day retention

### Disaster Recovery
- Automated failover
- Read replicas for scaling
- Cross-region replication

## Security

### Data Protection
- Passwords hashed with bcrypt
- Tokens encrypted at rest
- SSL/TLS for connections
- Row-level security (future)

### Access Control
- Application-level authorization
- Database user permissions
- Audit logging

## Future Enhancements

1. **Partitioning**
   - Partition logs by date
   - Improve query performance
   - Easier data archival

2. **Read Replicas**
   - Separate read/write workloads
   - Scale read operations
   - Reduce primary load

3. **Full-Text Search**
   - PostgreSQL full-text search
   - Search deployment logs
   - Search commit messages

4. **Time-Series Data**
   - TimescaleDB for metrics
   - Efficient time-based queries
   - Automatic data retention

## Conclusion

AutoStack's database schema is designed for scalability, performance, and data integrity. The use of PostgreSQL with SQLAlchemy's async ORM provides a solid foundation for a production deployment platform, with room for future enhancements as the system grows.
