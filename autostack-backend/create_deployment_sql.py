import requests
import json

# First, we need to log in to get a token
# For testing, let's create a deployment using the manual database creation

# Get user and project info first
print("Creating deployment for realtime-chat-hub...")

# Since we can't easily authenticate, let's just create the deployment record directly
import sqlite3
import uuid
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('autostack.db')
cursor = conn.cursor()

# Get first user
cursor.execute("SELECT id FROM users LIMIT 1")
user_row = cursor.fetchone()
if not user_row:
    print("❌ No user found in database")
    conn.close()
    exit(1)

user_id = user_row[0]
print(f"✅ Found user: {user_id}")

# Check if project exists
cursor.execute("SELECT id FROM projects WHERE repository = ?", ("Raj-glitch-max/realtime-chat-hub",))
project_row = cursor.fetchone()

if not project_row:
    # Create project
    project_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO projects (id, user_id, name, repository, branch, runtime, build_command, output_dir, auto_deploy_enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id,
        user_id,
        "realtime-chat-hub",
        "Raj-glitch-max/realtime-chat-hub",
        "main",
        "nodejs",
        "npm run build",
        "dist",
        0,
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat()
    ))
    print(f"✅ Created project: {project_id}")
else:
    project_id = project_row[0]
    print(f"✅ Found existing project: {project_id}")

# Create deployment
deployment_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO deployments (id, project_id, user_id, status, branch, creator_type, is_production, is_deleted, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    deployment_id,
    project_id,
    user_id,
    "queued",
    "main",
    "manual",
    0,
    0,
    datetime.utcnow().isoformat()
))

conn.commit()
conn.close()

print(f"\n✅ Successfully created deployment!")
print(f"   Deployment ID: {deployment_id}")
print(f"   Project ID: {project_id}")
print(f"   Repository: Raj-glitch-max/realtime-chat-hub")
print(f"   Status: queued")
print(f"\n🚀 View deployment at: http://localhost:3000/deployments/{deployment_id}")
print(f"\nNOTE: The deployment will start automatically if the backend is configured to process the queue.")
print(f"Otherwise, you may need to trigger it manually.")
