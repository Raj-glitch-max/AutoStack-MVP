import sqlite3
import uuid
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('autostack.db')
cursor = conn.cursor()

# Check deployments table schema
print("Checking deployments table schema...")
cursor.execute('PRAGMA table_info(deployments)')
deployment_columns = [row[1] for row in cursor.fetchall()]
print(f"Columns in deployments: {deployment_columns}")

# Get first user
cursor.execute("SELECT id, email FROM users LIMIT 1")
user_row = cursor.fetchone()
if not user_row:
    print("❌ No user found in database")
    conn.close()
    exit(1)

user_id = user_row[0]
user_email = user_row[1]
print(f"✅ Found user: {user_email} ({user_id})")

# Check if project exists
cursor.execute("SELECT id, name FROM projects WHERE repository = ?", ("Raj-glitch-max/realtime-chat-hub",))
project_row = cursor.fetchone()

if not project_row:
    # Create project with only required fields
    project_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO projects (id, user_id, name, repository, branch, build_command, output_dir, auto_deploy_enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project_id,
        user_id,
        "realtime-chat-hub",
        "Raj-glitch-max/realtime-chat-hub",
        "main",
        "npm run build",
        "dist",
        0,
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat()
    ))
    print(f"✅ Created project: realtime-chat-hub ({project_id})")
else:
    project_id = project_row[0]
    project_name = project_row[1]
    print(f"✅ Found existing project: {project_name} ({project_id})")

# Create deployment with only fields that exist
deployment_id = str(uuid.uuid4())

# Build INSERT based on available columns
fields = []
values = []

# Required fields
fields.extend(['id', 'project_id', 'user_id', 'status', 'branch', 'created_at'])
values.extend([deployment_id, project_id, user_id, "queued", "main", datetime.utcnow().isoformat()])

# Optional fields based on schema
if 'creator_type' in deployment_columns:
    fields.append('creator_type')
    values.append('manual')
if 'is_production' in deployment_columns:
    fields.append('is_production')
    values.append(0)
if 'is_deleted' in deployment_columns:
    fields.append('is_deleted')
    values.append(0)

placeholders = ", ".join(["?" for _ in fields])
field_names = ", ".join(fields)

cursor.execute(f"INSERT INTO deployments ({field_names}) VALUES ({placeholders})", tuple(values))

conn.commit()
conn.close()

print(f"\n✅ Successfully created deployment!")
print(f"   Deployment ID: {deployment_id}")
print(f"   Project ID: {project_id}")
print(f"   Repository: Raj-glitch-max/realtime-chat-hub")
print(f"   Status: queued")
print(f"\n🚀 View deployment at: http://localhost:3000/deployments/{deployment_id}")
print(f"\nℹ️  The deployment is now queued. Refresh your browser to see it!")
