# AutoStack - All Diagrams in PlantUML Format

This file contains all diagrams from the documentation in PlantUML format for easy visualization.

---

## FRONTEND DIAGRAMS

### Diagram 1: Component Hierarchy

**Description**: Shows the main component hierarchy from entry point to pages

\`\`\`plantuml
@startuml Component_Hierarchy
!define RECTANGLE class

RECTANGLE "main.tsx" as main
RECTANGLE "App.tsx" as app
RECTANGLE "AuthProvider" as auth
RECTANGLE "Router" as router
RECTANGLE "Layout" as layout
RECTANGLE "Protected Routes" as protected
RECTANGLE "Public Routes" as public

RECTANGLE "Dashboard" as dashboard
RECTANGLE "Deployments" as deployments
RECTANGLE "Deploy" as deploy
RECTANGLE "Analytics" as analytics
RECTANGLE "Settings" as settings

RECTANGLE "Landing" as landing
RECTANGLE "Login" as login
RECTANGLE "Signup" as signup

main --> app
app --> auth
auth --> router
router --> layout
layout --> protected
router --> public

protected --> dashboard
protected --> deployments
protected --> deploy
protected --> analytics
protected --> settings

public --> landing
public --> login
public --> signup

@enduml
\`\`\`

---

### Diagram 2: Routing Structure

**Description**: Shows all routes and their corresponding pages

\`\`\`plantuml
@startuml Routing_Structure
!define ROUTE rectangle

ROUTE "/" as root #LightBlue
ROUTE "/login" as login_route #LightBlue
ROUTE "/signup" as signup_route #LightBlue
ROUTE "/dashboard" as dashboard_route #LightGreen
ROUTE "/deployments" as deployments_route #LightGreen
ROUTE "/deployments/:id" as deployment_detail_route #LightGreen
ROUTE "/deploy" as deploy_route #LightGreen
ROUTE "/analytics" as analytics_route #LightGreen
ROUTE "/settings" as settings_route #LightGreen
ROUTE "/status" as status_route #LightGreen

rectangle "Landing Page" as landing_page
rectangle "Login Page" as login_page
rectangle "Signup Page" as signup_page
rectangle "Dashboard" as dashboard_page
rectangle "Deployments List" as deployments_page
rectangle "Deployment Detail" as deployment_detail_page
rectangle "Deploy Page" as deploy_page
rectangle "Analytics" as analytics_page
rectangle "Settings" as settings_page
rectangle "Status Page" as status_page

root --> landing_page
login_route --> login_page
signup_route --> signup_page
dashboard_route --> dashboard_page
deployments_route --> deployments_page
deployment_detail_route --> deployment_detail_page
deploy_route --> deploy_page
analytics_route --> analytics_page
settings_route --> settings_page
status_route --> status_page

note right of dashboard_page
  Protected Routes
  (Require Authentication)
end note

@enduml
\`\`\`

---

### Diagram 3: Authentication Flow - Email/Password

**Description**: Sequence diagram for email/password authentication

\`\`\`plantuml
@startuml Authentication_Email_Password
actor User
participant "Frontend" as F
participant "Backend" as B

User -> F: Click Login
F -> User: Show login form

User -> F: Enter email & password
F -> B: POST /api/auth/login\n{email, password}
B -> B: Validate credentials
B -> B: Hash password & compare
B -> F: Return JWT tokens\n{access_token, refresh_token}
F -> F: Store tokens in localStorage
F -> User: Redirect to dashboard

@enduml
\`\`\`

---

### Diagram 4: Authentication Flow - GitHub OAuth

**Description**: Sequence diagram for GitHub OAuth authentication

\`\`\`plantuml
@startuml Authentication_GitHub_OAuth
actor User
participant "Frontend" as F
participant "Backend" as B
participant "GitHub" as GH

User -> F: Click "Login with GitHub"
F -> GH: Redirect to GitHub OAuth
GH -> User: Request authorization
User -> GH: Approve access
GH -> F: Redirect with auth code
F -> B: POST /api/auth/github/callback\n{code}
B -> GH: Exchange code for token
GH -> B: Return access token
B -> B: Create/update user
B -> F: Return JWT tokens
F -> F: Store tokens
F -> User: Redirect to dashboard

@enduml
\`\`\`

---

### Diagram 5: Authentication Flow - Google OAuth

**Description**: Sequence diagram for Google OAuth authentication

\`\`\`plantuml
@startuml Authentication_Google_OAuth
actor User
participant "Frontend" as F
participant "Backend" as B
participant "Google" as G

User -> F: Click "Login with Google"
F -> G: Redirect to Google OAuth
G -> User: Request authorization
User -> G: Approve access
G -> F: Redirect with auth code
F -> B: POST /api/auth/google/callback\n{code}
B -> G: Exchange code for token
G -> B: Return access token
B -> B: Create/update user
B -> F: Return JWT tokens
F -> F: Store tokens
F -> User: Redirect to dashboard

@enduml
\`\`\`

---

### Diagram 6: Deployment Creation Flow

**Description**: Flowchart showing deployment creation process

\`\`\`plantuml
@startuml Deployment_Creation_Flow
start

:User on Deploy Page;

if (Select Source?) then (GitHub Repo)
  :Enter Repository URL;
else (Manual)
  :Upload Files;
endif

:Configure Build Settings;
:Set Environment Variables;
:Choose Branch;
:Submit Deployment;

:Backend Creates Deployment;
:Redirect to Deployment Detail;
:Stream Logs via WebSocket;

stop
@enduml
\`\`\`

---

### Diagram 7: Dashboard Components

**Description**: Shows dashboard component structure

\`\`\`plantuml
@startuml Dashboard_Components
rectangle "Dashboard Page" as dashboard {
  rectangle "Stats Cards" as stats {
    rectangle "Total Deployments" as total
    rectangle "Success Rate" as success
    rectangle "Active Containers" as active
    rectangle "Failed Deployments" as failed
  }
  
  rectangle "Recent Deployments" as recent {
    rectangle "Deployment List" as list
    rectangle "Status Badges" as badges
    rectangle "Quick Links" as links
  }
  
  rectangle "Quick Actions" as actions
  rectangle "Activity Timeline" as timeline
}

@enduml
\`\`\`

---

### Diagram 8: Data Flow Architecture

**Description**: Shows how data flows through the frontend

\`\`\`plantuml
@startuml Frontend_Data_Flow
rectangle "User Action" as action
rectangle "Component" as component
rectangle "React Query" as query #FFE4B5
rectangle "React Query Mutation" as mutation #FFE4B5
rectangle "API Request" as api
rectangle "Backend API" as backend
rectangle "Response" as response
rectangle "Cache Update" as cache #90EE90
rectangle "UI Re-render" as ui

action --> component
component --> query : Query
component --> mutation : Mutation
query --> api
mutation --> api
api --> backend
backend --> response
response --> cache
cache --> ui

@enduml
\`\`\`

---

## BACKEND DIAGRAMS

### Diagram 9: High-Level System Architecture

**Description**: Complete system architecture showing all components

\`\`\`plantuml
@startuml System_Architecture
!define COMPONENT rectangle

package "Client Layer" {
  COMPONENT "Frontend React App" as frontend
  COMPONENT "Mobile App" as mobile
  COMPONENT "CLI Tool" as cli
}

package "API Gateway" {
  COMPONENT "FastAPI Application" as fastapi #4169E1
  COMPONENT "WebSocket Server" as websocket #4169E1
}

package "Business Logic" {
  COMPONENT "Build Engine" as build #FFD700
  COMPONENT "Container Runtime" as container #FFD700
  COMPONENT "Jenkins Client" as jenkins
  COMPONENT "Monitoring Service" as monitoring
}

package "Data Layer" {
  database "PostgreSQL" as postgres #32CD32
  database "Redis Cache" as redis
}

package "External Services" {
  cloud "GitHub API" as github
  cloud "Google OAuth" as google
  cloud "Docker Engine" as docker
  cloud "Jenkins Server" as jenkins_server
  cloud "Kubernetes Cluster" as k8s
}

frontend --> fastapi
mobile --> fastapi
cli --> fastapi
frontend --> websocket

fastapi --> build
fastapi --> container
fastapi --> jenkins
fastapi --> monitoring

build --> postgres
container --> postgres
jenkins --> postgres
monitoring --> postgres

fastapi --> redis

build --> docker
container --> docker
jenkins --> jenkins_server
container --> k8s

fastapi --> github
fastapi --> google

@enduml
\`\`\`

---

### Diagram 10: Request Flow Sequence

**Description**: Shows how a request flows through the backend

\`\`\`plantuml
@startuml Request_Flow
actor Client
participant "Middleware" as M
participant "Router" as R
participant "Service" as S
database "Database" as D
participant "External API" as E

Client -> M: HTTP Request
M -> M: CORS Check
M -> M: JWT Validation
M -> R: Forward Request
R -> R: Validate Input (Pydantic)
R -> S: Call Service Method
S -> D: Query Database
D -> S: Return Data
S -> E: Call External API\n(if needed)
E -> S: Return Response
S -> R: Return Result
R -> R: Serialize Response
R -> Client: JSON Response

@enduml
\`\`\`

---

### Diagram 11: Deployment Flow - Dockerfile Mode

**Description**: Complete deployment flow for Dockerfile-based projects

\`\`\`plantuml
@startuml Deployment_Flow_Dockerfile
start

:Deployment Created;
:Queue Job;
:Clone Repository;

if (Dockerfile Detected?) then (Yes)
  :Docker Build Mode;
  :Detect Lambda Base Image;
  :Build Docker Image;
  :Start Container;
  :Health Check;
  :Fetch Container Logs;
  :Mark Success #90EE90;
else (No)
  :Node.js Build Mode;
  :Install Dependencies;
  :Run Build Command;
  :Copy Artifacts;
  
  if (Jenkins Enabled?) then (Yes)
    :Trigger Jenkins;
  endif
  
  :Mark Success #90EE90;
endif

:Update Deployment Status;
:Broadcast WebSocket Event;

stop
@enduml
\`\`\`

---

## DATABASE DIAGRAMS

### Diagram 12: Entity Relationship Diagram (Complete)

**Description**: Complete ER diagram showing all tables and relationships

\`\`\`plantuml
@startuml Complete_ER_Diagram
entity "User" as user {
  * id : UUID <<PK>>
  --
  * name : VARCHAR(255)
  * email : VARCHAR(255) <<UK>>
  password_hash : VARCHAR(255)
  avatar_url : TEXT
  github_id : VARCHAR(255) <<UK>>
  google_id : VARCHAR(255) <<UK>>
  * email_verified : BOOLEAN
  * created_at : TIMESTAMP
  * updated_at : TIMESTAMP
}

entity "Project" as project {
  * id : UUID <<PK>>
  * user_id : UUID <<FK>>
  --
  * name : VARCHAR(255)
  * repository : VARCHAR(255)
  * branch : VARCHAR(100)
  * build_command : TEXT
  * output_dir : VARCHAR(255)
  env_vars : TEXT
  github_repo_id : VARCHAR(255)
  * runtime : VARCHAR(50)
  * auto_deploy_enabled : BOOLEAN
  auto_deploy_branch : VARCHAR(100)
  jenkins_job_name : VARCHAR(255)
  * created_at : TIMESTAMP
  * updated_at : TIMESTAMP
}

entity "Deployment" as deployment {
  * id : UUID <<PK>>
  * project_id : UUID <<FK>>
  * user_id : UUID <<FK>>
  --
  * status : VARCHAR(50)
  branch : VARCHAR(100)
  commit_hash : VARCHAR(40)
  commit_message : TEXT
  author : VARCHAR(255)
  commit_timestamp : TIMESTAMP
  * creator_type : VARCHAR(20)
  * is_production : BOOLEAN
  env_vars : TEXT
  build_duration_seconds : INTEGER
  failed_reason : TEXT
  deployed_url : TEXT
  started_at : TIMESTAMP
  completed_at : TIMESTAMP
  * created_at : TIMESTAMP
  * is_deleted : BOOLEAN
}

entity "DeploymentContainer" as container {
  * id : UUID <<PK>>
  * deployment_id : UUID <<FK>>
  --
  * container_id : VARCHAR(255)
  * image : VARCHAR(255)
  * host : VARCHAR(255)
  * port : INTEGER
  * status : VARCHAR(50)
  * created_at : TIMESTAMP
  stopped_at : TIMESTAMP
}

entity "DeploymentLog" as log {
  * id : UUID <<PK>>
  * deployment_id : UUID <<FK>>
  --
  * timestamp : TIMESTAMP
  log_level : VARCHAR(20)
  * message : TEXT
  * created_at : TIMESTAMP
}

entity "DeploymentStage" as stage {
  * id : UUID <<PK>>
  * deployment_id : UUID <<FK>>
  --
  * stage_name : VARCHAR(50)
  * status : VARCHAR(50)
  started_at : TIMESTAMP
  completed_at : TIMESTAMP
  error_message : TEXT
  * created_at : TIMESTAMP
}

entity "DeploymentHealthCheck" as health {
  * id : UUID <<PK>>
  * deployment_id : UUID <<FK>>
  --
  * url : TEXT
  http_status : INTEGER
  latency_ms : INTEGER
  * is_live : BOOLEAN
  * checked_at : TIMESTAMP
}

entity "DeploymentRuntimeLog" as runtime_log {
  * id : UUID <<PK>>
  * deployment_id : UUID <<FK>>
  --
  * source : VARCHAR(50)
  log_level : VARCHAR(20)
  * message : TEXT
  * timestamp : TIMESTAMP
}

entity "UserPreferences" as prefs {
  * id : UUID <<PK>>
  * user_id : UUID <<FK>> <<UK>>
  --
  * theme : VARCHAR(20)
  * email_notifications : BOOLEAN
  * deployment_success_notifications : BOOLEAN
  * deployment_failure_notifications : BOOLEAN
  * created_at : TIMESTAMP
  * updated_at : TIMESTAMP
}

entity "GithubConnection" as github {
  * id : UUID <<PK>>
  * user_id : UUID <<FK>> <<UK>>
  --
  github_username : VARCHAR(255)
  * github_access_token : TEXT
  github_refresh_token : TEXT
  token_expires_at : TIMESTAMP
  scope : TEXT
  * connected_at : TIMESTAMP
}

entity "Session" as session {
  * id : UUID <<PK>>
  * user_id : UUID <<FK>>
  --
  * token : VARCHAR(255) <<UK>>
  * expires_at : TIMESTAMP
  * created_at : TIMESTAMP
}

entity "PasswordResetToken" as reset {
  * id : UUID <<PK>>
  * user_id : UUID <<FK>>
  --
  * token_hash : VARCHAR(255)
  * expires_at : TIMESTAMP
  used_at : TIMESTAMP
  * created_at : TIMESTAMP
}

entity "WebhookPayload" as webhook {
  * id : UUID <<PK>>
  deployment_id : UUID <<FK>>
  --
  * provider : VARCHAR(50)
  * payload_json : JSONB
  * headers : JSONB
  * received_at : TIMESTAMP
}

' Relationships
user ||--o{ project : "owns"
user ||--o{ deployment : "creates"
user ||--o| prefs : "has"
user ||--o| github : "has"
user ||--o{ session : "has"
user ||--o{ reset : "has"

project ||--o{ deployment : "contains"

deployment ||--o{ log : "generates"
deployment ||--o{ stage : "tracks"
deployment ||--o| container : "runs"
deployment ||--o{ health : "monitors"
deployment ||--o{ runtime_log : "produces"
deployment ||--o{ webhook : "triggers"

@enduml
\`\`\`

---

### Diagram 13: Core Tables Relationship (Simplified)

**Description**: Simplified view of core tables (User, Project, Deployment)

\`\`\`plantuml
@startuml Core_Tables_Relationship
entity "User" as user {
  * id : UUID
  * email : VARCHAR
  * name : VARCHAR
}

entity "Project" as project {
  * id : UUID
  * user_id : UUID
  * name : VARCHAR
  * repository : VARCHAR
}

entity "Deployment" as deployment {
  * id : UUID
  * project_id : UUID
  * user_id : UUID
  * status : VARCHAR
  * deployed_url : TEXT
}

user ||--o{ project
user ||--o{ deployment
project ||--o{ deployment

@enduml
\`\`\`

---

### Diagram 14: Deployment Related Tables

**Description**: Shows all tables related to deployments

\`\`\`plantuml
@startuml Deployment_Related_Tables
entity "Deployment" as deployment #LightBlue {
  * id : UUID
  * status : VARCHAR
}

entity "DeploymentLog" as log {
  * id : UUID
  * deployment_id : UUID
  * message : TEXT
}

entity "DeploymentStage" as stage {
  * id : UUID
  * deployment_id : UUID
  * stage_name : VARCHAR
  * status : VARCHAR
}

entity "DeploymentContainer" as container {
  * id : UUID
  * deployment_id : UUID
  * container_id : VARCHAR
  * port : INTEGER
}

entity "DeploymentHealthCheck" as health {
  * id : UUID
  * deployment_id : UUID
  * is_live : BOOLEAN
}

entity "DeploymentRuntimeLog" as runtime {
  * id : UUID
  * deployment_id : UUID
  * source : VARCHAR
  * message : TEXT
}

deployment ||--o{ log
deployment ||--o{ stage
deployment ||--o| container
deployment ||--o{ health
deployment ||--o{ runtime

@enduml
\`\`\`

---

## How to Use These Diagrams

### Option 1: Online PlantUML Editor
1. Go to http://www.plantuml.com/plantuml/uml/
2. Copy any diagram code above
3. Paste it into the editor
4. View the rendered diagram

### Option 2: VS Code Extension
1. Install "PlantUML" extension in VS Code
2. Create a new file with `.puml` extension
3. Paste the diagram code
4. Press Alt+D to preview

### Option 3: PlantUML Server
1. Install PlantUML locally
2. Run: `java -jar plantuml.jar diagram.puml`
3. Get PNG/SVG output

---

## Diagram Index

**Frontend Diagrams:**
1. Component Hierarchy
2. Routing Structure
3. Authentication Flow - Email/Password
4. Authentication Flow - GitHub OAuth
5. Authentication Flow - Google OAuth
6. Deployment Creation Flow
7. Dashboard Components
8. Data Flow Architecture

**Backend Diagrams:**
9. High-Level System Architecture
10. Request Flow Sequence
11. Deployment Flow - Dockerfile Mode

**Database Diagrams:**
12. Entity Relationship Diagram (Complete)
13. Core Tables Relationship (Simplified)
14. Deployment Related Tables

---

**Total Diagrams**: 14 comprehensive diagrams in PlantUML format
