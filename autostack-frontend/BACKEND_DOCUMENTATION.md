# Autostack - Backend Integration Documentation

## Project Overview
Autostack is a modern deployment platform for indie developers and startups. This document provides comprehensive details for backend engineers to implement the necessary APIs, database schemas, and integrations.

---

## Table of Contents
1. [Application Routes](#application-routes)
2. [Page Components & Features](#page-components--features)
3. [API Endpoints Required](#api-endpoints-required)
4. [Database Schema](#database-schema)
5. [Authentication & Authorization](#authentication--authorization)
6. [Real-time Features](#real-time-features)
7. [External Integrations](#external-integrations)

---

## Application Routes

### Public Routes
| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Landing.tsx | Landing page with hero, features, how-it-works |
| `/login` | Login.tsx | User login with email/password and OAuth |
| `/signup` | Signup.tsx | User registration with email/password and OAuth |
| `/forgot-password` | ForgotPassword.tsx | Password reset request |

### Protected Routes (Require Authentication)
| Route | Component | Description |
|-------|-----------|-------------|
| `/dashboard` | DashboardPage.tsx | Main dashboard with stats and recent deployments |
| `/deploy` | DeployPage.tsx | New deployment creation wizard (3 steps) |
| `/deployments` | DeploymentsPage.tsx | List of all deployments with filters |
| `/deployments/:id` | DeploymentDetail.tsx | Detailed deployment view with logs |
| `/settings` | Settings.tsx | User settings and preferences |
| `/status` | StatusPage.tsx | Real-time system status and health monitoring |
| `/analytics` | AnalyticsPage.tsx | Analytics dashboard with charts |

### Coming Soon Routes
| Route | Component | Description |
|-------|-----------|-------------|
| `/pricing` | PricingComingSoon | Pricing plans page |
| `/docs` | DocsComingSoon | Documentation |
| `/templates` | TemplatesComingSoon | Deployment templates |
| `/pipelines` | PipelinesComingSoon | CI/CD pipelines |
| `/monitoring` | MonitoringComingSoon | Advanced monitoring |
| `/team` | TeamComingSoon | Team collaboration |
| `/integrations` | IntegrationsComingSoon | Third-party integrations |

---

## Page Components & Features

### 1. Landing Page (`/`)
**Features:**
- Hero section with CTA buttons
- Feature bento grid (4 features: GitHub Integration, Lightning Fast, Secure by Default, Global CDN)
- "How it works" timeline (3 steps)
- CTA section with "Get Started" button
- Footer with links

**Actions:**
- Navigate to `/signup`
- Navigate to `/login`

---

### 2. Login Page (`/login`)
**Features:**
- Email/password login form
- "Remember me" checkbox
- "Forgot password?" link
- GitHub OAuth button
- Google OAuth button
- "Sign up" link

**Required APIs:**
- `POST /api/auth/login` - Email/password authentication
- `GET /api/auth/github` - GitHub OAuth initiation
- `GET /api/auth/google` - Google OAuth initiation
- `GET /api/auth/github/callback` - GitHub OAuth callback
- `GET /api/auth/google/callback` - Google OAuth callback

**Validation:**
- Email format validation
- Password required

**Success Flow:**
- Show success toast
- Redirect to `/dashboard`

---

### 3. Signup Page (`/signup`)
**Features:**
- Full name input
- Email input
- Password input (min 8 characters)
- GitHub OAuth button
- Google OAuth button
- "Sign in" link
- Terms of Service and Privacy Policy links

**Required APIs:**
- `POST /api/auth/signup` - User registration
- `GET /api/auth/github` - GitHub OAuth initiation
- `GET /api/auth/google` - Google OAuth initiation

**Validation:**
- Name required
- Email format validation
- Password minimum 8 characters

**Success Flow:**
- Show success toast
- Redirect to `/dashboard`

---

### 4. Forgot Password Page (`/forgot-password`)
**Features:**
- Email input
- "Send reset link" button
- Success state with confirmation message
- "Back to login" link

**Required APIs:**
- `POST /api/auth/forgot-password` - Send password reset email

---

### 5. Dashboard Page (`/dashboard`)
**Features:**
- Statistics cards:
  - Total Deployments (with weekly change)
  - Active Projects (with today's count)
  - Success Rate (with monthly change)
  - Average Deploy Time (with improvement)
- Recent deployments table (5 most recent)
- "New Deployment" button
- "Connect GitHub" banner (if not connected)
- Quick actions section

**Required APIs:**
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/deployments/recent` - Recent deployments (limit 5)
- `GET /api/github/connection-status` - Check if GitHub is connected

**Response Example:**
```json
{
  "stats": {
    "totalDeployments": 24,
    "weeklyChange": "+3",
    "activeProjects": 8,
    "todayDeployments": 2,
    "successRate": 96,
    "monthlySuccessChange": 2,
    "avgDeployTime": "2.4m",
    "timeImprovement": "-18s"
  },
  "recentDeployments": [
    {
      "id": "dep_001",
      "repo": "my-awesome-app",
      "branch": "main",
      "status": "success",
      "timestamp": "2025-01-20T10:30:00Z",
      "duration": "2m 15s",
      "author": "john.doe"
    }
  ]
}
```

---

### 6. Deploy Page (`/deploy`)
**Features:**
- 3-step wizard:
  1. Select Repository
  2. Configure Build
  3. Deploy
- Step 1: GitHub repository dropdown
- Step 2: 
  - Branch selection
  - Build command input
  - Output directory input
  - Environment variables textarea
- Step 3: Deploy button with confirmation

**Required APIs:**
- `GET /api/github/repos` - List user's GitHub repositories
- `POST /api/deployments` - Create new deployment

**Request Example:**
```json
{
  "repository": "my-awesome-app",
  "branch": "main",
  "buildCommand": "npm run build",
  "outputDir": "dist",
  "envVars": "NODE_ENV=production\nAPI_URL=https://api.example.com"
}
```

**Success Flow:**
- Show deployment started toast
- Redirect to `/deployments` after 2 seconds

---

### 7. Deployments Page (`/deployments`)
**Features:**
- Search bar (filter by repo name)
- Status filter dropdown (All, Success, Failed, Building)
- Deployments table with columns:
  - Repository
  - Branch
  - Status (with badge)
  - Author
  - Commit hash
  - Duration
  - Timestamp
- "View Logs" button for each deployment
- Skeleton loaders while loading
- Pagination

**Required APIs:**
- `GET /api/deployments` - List all deployments with filters

**Query Parameters:**
- `search` - Repository name filter
- `status` - Status filter (all, success, failed, building)
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 10)

**Response Example:**
```json
{
  "deployments": [
    {
      "id": "dep_001",
      "repo": "my-awesome-app",
      "branch": "main",
      "status": "success",
      "author": "john.doe",
      "commit": "a7f8c9d",
      "duration": "2m 34s",
      "timestamp": "2025-01-20T10:30:00Z",
      "url": "https://my-awesome-app.autostack.app"
    }
  ],
  "pagination": {
    "currentPage": 1,
    "totalPages": 5,
    "totalItems": 47
  }
}
```

---

### 8. Deployment Detail Page (`/deployments/:id`)
**Features:**
- Deployment header with:
  - Repository name
  - Branch badge
  - Status badge
  - Timestamp
- Build stages with progress:
  - Queued
  - Building
  - Deploying
  - Success/Failed
- Real-time log viewer with:
  - Color-coded log lines
  - Auto-scroll functionality
  - Pausable scrolling
- Action buttons:
  - "Visit Site" (opens deployed URL)
  - "Copy URL" (copies to clipboard)
  - "Back to Deployments"

**Required APIs:**
- `GET /api/deployments/:id` - Get deployment details
- `GET /api/deployments/:id/logs` - Get deployment logs (streaming or paginated)
- `WS /api/deployments/:id/logs/stream` - WebSocket for real-time log streaming

**Response Example:**
```json
{
  "id": "dep_001",
  "repo": "my-awesome-app",
  "branch": "main",
  "status": "success",
  "timestamp": "2025-01-20T10:30:00Z",
  "url": "https://my-awesome-app.autostack.app",
  "stages": [
    {
      "name": "Queued",
      "status": "completed",
      "timestamp": "2025-01-20T10:30:00Z"
    },
    {
      "name": "Building",
      "status": "completed",
      "timestamp": "2025-01-20T10:30:15Z"
    },
    {
      "name": "Deploying",
      "status": "completed",
      "timestamp": "2025-01-20T10:32:00Z"
    },
    {
      "name": "Success",
      "status": "completed",
      "timestamp": "2025-01-20T10:32:45Z"
    }
  ],
  "logs": [
    "[00:00] Starting deployment...",
    "[00:05] Cloning repository...",
    "[00:15] Installing dependencies...",
    "[01:30] Building application...",
    "[02:15] Deployment successful!"
  ]
}
```

---

### 9. Settings Page (`/settings`)
**Features:**
- Tabs:
  1. Profile
  2. GitHub
  3. Notifications
  4. Appearance
- Profile tab:
  - Name input
  - Email input (disabled)
  - Avatar display
  - "Save Changes" button
- GitHub tab:
  - Connection status
  - "Connect GitHub" button (if not connected)
  - Connected account info (if connected)
  - "Disconnect" button
- Notifications tab:
  - Email notifications toggle
  - Deployment success notifications toggle
  - Deployment failure notifications toggle
- Appearance tab:
  - Theme selector (Light/Dark/System)

**Required APIs:**
- `GET /api/user/profile` - Get user profile
- `PUT /api/user/profile` - Update user profile
- `GET /api/github/connection` - Get GitHub connection status
- `POST /api/github/connect` - Initiate GitHub connection
- `DELETE /api/github/disconnect` - Disconnect GitHub
- `GET /api/user/preferences` - Get user preferences
- `PUT /api/user/preferences` - Update user preferences

---

### 10. Status Page (`/status`)
**Features:**
- Overall status banner (All Systems Operational / Some Systems Degraded)
- Service status cards (4 services):
  - API Gateway (uptime %, response time)
  - Database (uptime %, response time)
  - CDN (uptime %, response time)
  - Build Service (uptime %, response time)
- Platform metrics cards:
  - Total Deployments (with % change)
  - Active Projects (with % change)
  - Avg Deploy Time (with % change)
  - Success Rate (with % change)
- Historical performance (last 90 days)
- Recent incidents section
- Live updates every 3 seconds

**Required APIs:**
- `GET /api/status/services` - Get current status of all services
- `GET /api/status/metrics` - Get platform metrics
- `GET /api/status/history` - Get historical performance data
- `GET /api/status/incidents` - Get recent incidents
- `WS /api/status/stream` - WebSocket for real-time status updates

**Response Example:**
```json
{
  "services": [
    {
      "name": "API Gateway",
      "status": "operational",
      "uptime": 99.98,
      "responseTime": 45
    }
  ],
  "metrics": {
    "totalDeployments": 12458,
    "deploymentChange": 15.3,
    "activeProjects": 3247,
    "projectChange": 8.2,
    "avgDeployTime": "42s",
    "timeChange": -12.5,
    "successRate": "99.8%",
    "successChange": 0.3
  },
  "history": [
    {
      "date": "30 days ago",
      "uptime": 99.95,
      "incidents": 2
    }
  ]
}
```

---

### 11. Analytics Page (`/analytics`)
**Features:**
- Key metrics cards:
  - Total Deployments (with % change)
  - Success Rate (with % change)
  - Avg Build Time (with % change)
  - Active Projects (with % change)
- Tabs with charts:
  1. **Frequency Tab:**
     - Area chart: Deployment frequency over 6 weeks
     - Bar chart: Hourly deployment distribution
  2. **Success Rate Tab:**
     - Line chart: Success vs Failed rates (weekly)
     - Pie chart: Status distribution (Success, Failed, Cancelled)
  3. **Build Duration Tab:**
     - Multi-line chart: Avg, Min, Max build times over 6 weeks
     - Cards: Fastest build, Average build, Slowest build
  4. **Resources Tab:**
     - Horizontal bar chart: Current resource usage (CPU, Memory, Storage, Network)
     - Progress bars with percentages
     - System status and uptime

**Required APIs:**
- `GET /api/analytics/metrics` - Get key metrics
- `GET /api/analytics/deployment-frequency` - Get deployment frequency data
- `GET /api/analytics/success-rates` - Get success rate data
- `GET /api/analytics/build-durations` - Get build duration trends
- `GET /api/analytics/resource-usage` - Get resource usage data
- `GET /api/analytics/deployment-status` - Get deployment status distribution
- `GET /api/analytics/hourly-deployments` - Get hourly deployment patterns

**Response Example:**
```json
{
  "metrics": {
    "totalDeployments": 915,
    "deploymentsChange": 12.5,
    "successRate": 92.6,
    "successChange": 2.3,
    "avgBuildTime": "2m 8s",
    "buildTimeChange": -15.8,
    "activeProjects": 47,
    "projectsChange": 8.2
  },
  "deploymentFrequency": [
    {
      "date": "Jan 1",
      "deployments": 12
    }
  ],
  "successRates": [
    {
      "date": "Week 1",
      "success": 95,
      "failed": 5
    }
  ],
  "buildDurations": [
    {
      "date": "Jan 1",
      "avgDuration": 145,
      "minDuration": 90,
      "maxDuration": 220
    }
  ],
  "resourceUsage": [
    {
      "name": "CPU",
      "value": 65
    }
  ],
  "deploymentStatus": [
    {
      "name": "Success",
      "value": 847
    }
  ],
  "hourlyDeployments": [
    {
      "hour": "00:00",
      "deployments": 2
    }
  ]
}
```

---

## API Endpoints Required

### Authentication Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/signup` | User registration | No |
| POST | `/api/auth/login` | User login | No |
| POST | `/api/auth/logout` | User logout | Yes |
| POST | `/api/auth/forgot-password` | Request password reset | No |
| POST | `/api/auth/reset-password` | Reset password with token | No |
| GET | `/api/auth/github` | Initiate GitHub OAuth | No |
| GET | `/api/auth/github/callback` | GitHub OAuth callback | No |
| GET | `/api/auth/google` | Initiate Google OAuth | No |
| GET | `/api/auth/google/callback` | Google OAuth callback | No |
| GET | `/api/auth/session` | Get current session | Yes |
| POST | `/api/auth/refresh` | Refresh access token | Yes |

### User Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/user/profile` | Get user profile | Yes |
| PUT | `/api/user/profile` | Update user profile | Yes |
| GET | `/api/user/preferences` | Get user preferences | Yes |
| PUT | `/api/user/preferences` | Update preferences | Yes |
| DELETE | `/api/user/account` | Delete user account | Yes |

### Dashboard Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/dashboard/stats` | Get dashboard statistics | Yes |
| GET | `/api/deployments/recent` | Get recent deployments | Yes |

### Deployment Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/deployments` | List all deployments | Yes |
| POST | `/api/deployments` | Create new deployment | Yes |
| GET | `/api/deployments/:id` | Get deployment details | Yes |
| DELETE | `/api/deployments/:id` | Delete deployment | Yes |
| GET | `/api/deployments/:id/logs` | Get deployment logs | Yes |
| WS | `/api/deployments/:id/logs/stream` | Stream logs (WebSocket) | Yes |
| POST | `/api/deployments/:id/cancel` | Cancel deployment | Yes |
| POST | `/api/deployments/:id/redeploy` | Redeploy | Yes |

### GitHub Integration Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/github/repos` | List user repositories | Yes |
| GET | `/api/github/connection` | Get connection status | Yes |
| POST | `/api/github/connect` | Connect GitHub account | Yes |
| DELETE | `/api/github/disconnect` | Disconnect GitHub | Yes |
| GET | `/api/github/repos/:repo/branches` | Get repository branches | Yes |

### Status Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/status/services` | Get service status | No |
| GET | `/api/status/metrics` | Get platform metrics | No |
| GET | `/api/status/history` | Get historical data | No |
| GET | `/api/status/incidents` | Get recent incidents | No |
| WS | `/api/status/stream` | Real-time status updates | No |

### Analytics Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/analytics/metrics` | Get key metrics | Yes |
| GET | `/api/analytics/deployment-frequency` | Deployment frequency | Yes |
| GET | `/api/analytics/success-rates` | Success rate trends | Yes |
| GET | `/api/analytics/build-durations` | Build duration trends | Yes |
| GET | `/api/analytics/resource-usage` | Resource usage data | Yes |
| GET | `/api/analytics/deployment-status` | Status distribution | Yes |
| GET | `/api/analytics/hourly-deployments` | Hourly patterns | Yes |

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),
  avatar_url TEXT,
  github_id VARCHAR(255) UNIQUE,
  google_id VARCHAR(255) UNIQUE,
  email_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Projects Table
```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  repository VARCHAR(255) NOT NULL,
  branch VARCHAR(100) DEFAULT 'main',
  build_command TEXT DEFAULT 'npm run build',
  output_dir VARCHAR(255) DEFAULT 'dist',
  env_vars TEXT,
  github_repo_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Deployments Table
```sql
CREATE TABLE deployments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  status VARCHAR(50) DEFAULT 'queued', -- queued, building, deploying, success, failed, cancelled
  branch VARCHAR(100),
  commit_hash VARCHAR(40),
  commit_message TEXT,
  author VARCHAR(255),
  build_duration INTEGER, -- in seconds
  deployed_url TEXT,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Deployment Logs Table
```sql
CREATE TABLE deployment_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deployment_id UUID REFERENCES deployments(id) ON DELETE CASCADE,
  timestamp TIMESTAMP DEFAULT NOW(),
  log_level VARCHAR(20), -- info, warning, error
  message TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Deployment Stages Table
```sql
CREATE TABLE deployment_stages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deployment_id UUID REFERENCES deployments(id) ON DELETE CASCADE,
  stage_name VARCHAR(50) NOT NULL, -- queued, building, deploying, success, failed
  status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, failed
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### User Preferences Table
```sql
CREATE TABLE user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
  theme VARCHAR(20) DEFAULT 'system', -- light, dark, system
  email_notifications BOOLEAN DEFAULT TRUE,
  deployment_success_notifications BOOLEAN DEFAULT TRUE,
  deployment_failure_notifications BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### GitHub Connections Table
```sql
CREATE TABLE github_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
  github_username VARCHAR(255),
  github_access_token TEXT NOT NULL,
  github_refresh_token TEXT,
  token_expires_at TIMESTAMP,
  connected_at TIMESTAMP DEFAULT NOW()
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  token VARCHAR(255) UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Service Status Table (for Status Page)
```sql
CREATE TABLE service_status (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_name VARCHAR(100) NOT NULL,
  status VARCHAR(50) NOT NULL, -- operational, degraded, down
  uptime_percentage DECIMAL(5,2),
  response_time INTEGER, -- in milliseconds
  last_checked_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Incidents Table
```sql
CREATE TABLE incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(50) NOT NULL, -- investigating, identified, monitoring, resolved
  severity VARCHAR(50), -- minor, major, critical
  affected_services TEXT[], -- array of service names
  started_at TIMESTAMP NOT NULL,
  resolved_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Authentication & Authorization

### Authentication Flow
1. **Email/Password:**
   - Hash passwords using bcrypt (min 10 rounds)
   - Return JWT token on successful login
   - Include refresh token for token renewal

2. **OAuth (GitHub/Google):**
   - Redirect to OAuth provider
   - Handle callback with authorization code
   - Exchange code for access token
   - Fetch user profile
   - Create or update user account
   - Return JWT token

### JWT Token Structure
```json
{
  "userId": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "iat": 1234567890,
  "exp": 1234571490
}
```

### Authorization Rules
- All `/api/deployments/*` endpoints require authenticated user
- Users can only access their own deployments
- Users can only access their own projects
- Admin users (future) can access all resources

---

## Real-time Features

### WebSocket Connections

#### 1. Deployment Log Streaming
**Endpoint:** `WS /api/deployments/:id/logs/stream`

**Authentication:** Send JWT token in connection query parameter

**Events:**
```json
// Client → Server: Subscribe
{
  "type": "subscribe",
  "deploymentId": "dep_001"
}

// Server → Client: Log entry
{
  "type": "log",
  "timestamp": "2025-01-20T10:30:15Z",
  "level": "info",
  "message": "[00:15] Installing dependencies..."
}

// Server → Client: Status update
{
  "type": "status_update",
  "status": "building",
  "stage": "Building"
}

// Server → Client: Complete
{
  "type": "deployment_complete",
  "status": "success",
  "duration": "2m 34s",
  "url": "https://my-app.autostack.app"
}
```

#### 2. Status Page Real-time Updates
**Endpoint:** `WS /api/status/stream`

**Events:**
```json
// Server → Client: Service update
{
  "type": "service_update",
  "service": "API Gateway",
  "status": "operational",
  "uptime": 99.98,
  "responseTime": 45
}

// Server → Client: Metrics update
{
  "type": "metrics_update",
  "metrics": {
    "totalDeployments": 12458,
    "activeProjects": 3247
  }
}
```

---

## External Integrations

### GitHub Integration
**Required Scopes:**
- `repo` - Access to repositories
- `user:email` - Access to user email

**Webhook Events:**
- `push` - Trigger automatic deployment
- `pull_request` - Trigger preview deployment (future)

**API Calls:**
- List repositories
- Get repository branches
- Get commit information
- Clone repository for deployment

### Google OAuth
**Required Scopes:**
- `profile` - User profile information
- `email` - User email address

---

## Environment Variables

Backend needs the following environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/autostack

# JWT
JWT_SECRET=your-secret-key
JWT_EXPIRES_IN=7d
REFRESH_TOKEN_SECRET=your-refresh-secret
REFRESH_TOKEN_EXPIRES_IN=30d

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_CALLBACK_URL=https://autostack.app/api/auth/github/callback

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_CALLBACK_URL=https://autostack.app/api/auth/google/callback

# Email (for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@autostack.app
SMTP_PASS=your-email-password

# Application
APP_URL=https://autostack.app
FRONTEND_URL=https://autostack.app
NODE_ENV=production

# Build Service
BUILD_TIMEOUT=600000 # 10 minutes in milliseconds
MAX_BUILD_SIZE=500 # MB

# Storage (for build artifacts)
S3_BUCKET=autostack-builds
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret

# CDN
CDN_URL=https://cdn.autostack.app
```

---

## Error Handling

All API endpoints should return consistent error responses:

```json
{
  "error": {
    "code": "DEPLOYMENT_NOT_FOUND",
    "message": "Deployment with ID 'dep_001' not found",
    "statusCode": 404,
    "details": {}
  }
}
```

### Common Error Codes
- `UNAUTHORIZED` (401) - Not authenticated
- `FORBIDDEN` (403) - Not authorized to access resource
- `NOT_FOUND` (404) - Resource not found
- `VALIDATION_ERROR` (422) - Request validation failed
- `RATE_LIMIT_EXCEEDED` (429) - Too many requests
- `INTERNAL_SERVER_ERROR` (500) - Server error

---

## Rate Limiting

Implement rate limiting on all API endpoints:
- Authentication endpoints: 5 requests per minute per IP
- Deployment creation: 10 requests per hour per user
- General API: 100 requests per minute per user

---

## Deployment Process Flow

1. User submits deployment request
2. Backend validates request and creates deployment record with status "queued"
3. Backend adds deployment to job queue
4. Build worker picks up deployment:
   - Update status to "building"
   - Clone repository
   - Install dependencies
   - Run build command
   - Stream logs via WebSocket
5. On build success:
   - Update status to "deploying"
   - Upload build artifacts to storage
   - Deploy to CDN/edge network
   - Update status to "success"
   - Set deployed URL
6. On build failure:
   - Update status to "failed"
   - Store error logs
   - Send notification to user

---

## Security Considerations

1. **Input Validation:** Validate all user inputs to prevent injection attacks
2. **SQL Injection:** Use parameterized queries
3. **XSS Prevention:** Sanitize user-generated content
4. **CSRF Protection:** Implement CSRF tokens for state-changing operations
5. **Rate Limiting:** Prevent abuse and DDoS attacks
6. **Secure Headers:** Set appropriate security headers (HSTS, CSP, etc.)
7. **Environment Variables:** Store secrets securely, never in code
8. **GitHub Tokens:** Encrypt GitHub access tokens in database
9. **Build Isolation:** Run builds in isolated containers
10. **Log Sanitization:** Remove sensitive data from logs

---

## Performance Optimization

1. **Database Indexing:**
   - Index `user_id` in all user-related tables
   - Index `project_id` and `deployment_id` for foreign keys
   - Index `email` in users table
   - Index `status` in deployments table

2. **Caching:**
   - Cache user sessions in Redis
   - Cache GitHub repository lists (5 min TTL)
   - Cache dashboard statistics (1 min TTL)
   - Cache status page data (30 sec TTL)

3. **Query Optimization:**
   - Use pagination for list endpoints
   - Limit fields returned in API responses
   - Use database views for complex queries

4. **Asset Optimization:**
   - Compress build artifacts before storage
   - Use CDN for serving deployed applications
   - Implement lazy loading for logs

---

## Monitoring & Logging

1. **Application Metrics:**
   - Request count per endpoint
   - Response times
   - Error rates
   - Active WebSocket connections

2. **Business Metrics:**
   - Deployments per day
   - Success/failure rates
   - Average build times
   - User signups per day

3. **Logging:**
   - Log all API requests with request ID
   - Log authentication attempts
   - Log deployment lifecycle events
   - Log errors with stack traces
   - Use structured logging (JSON format)

---

## Testing Requirements

1. **Unit Tests:**
   - Test all API endpoint handlers
   - Test authentication logic
   - Test deployment validation
   - Test build process

2. **Integration Tests:**
   - Test complete deployment flow
   - Test OAuth flows
   - Test WebSocket connections
   - Test database operations

3. **E2E Tests:**
   - Test complete user journey from signup to deployment
   - Test GitHub integration
   - Test real-time features

---

## Deployment Architecture

```
┌─────────────────┐
│   Load Balancer │
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
┌───▼────┐ ┌──▼─────┐
│ API    │ │ API    │
│ Server │ │ Server │
│ (Node) │ │ (Node) │
└───┬────┘ └──┬─────┘
    │          │
    └────┬─────┘
         │
    ┌────▼──────────┐
    │   PostgreSQL  │
    │   Database    │
    └───────────────┘
         │
    ┌────▼──────────┐
    │  Redis Cache  │
    └───────────────┘
         │
    ┌────▼──────────┐
    │ Job Queue     │
    │ (Bull/Redis)  │
    └───┬───────────┘
        │
   ┌────▼────────┐
   │ Build       │
   │ Workers     │
   │ (Docker)    │
   └─────────────┘
```

---

## Next Steps for Backend Team

1. Set up database with schema
2. Implement authentication endpoints
3. Implement user management endpoints
4. Implement deployment endpoints
5. Set up GitHub OAuth integration
6. Set up Google OAuth integration
7. Implement build service with job queue
8. Implement WebSocket server for real-time features
9. Set up monitoring and logging
10. Write tests
11. Deploy to staging environment
12. Performance testing
13. Deploy to production

---

## Support & Questions

For questions or clarifications, contact the frontend team with:
- Specific API endpoint questions
- Data structure questions
- Real-time feature implementation details
- Authentication flow clarifications

---

**Last Updated:** January 2025
**Version:** 1.0.0
