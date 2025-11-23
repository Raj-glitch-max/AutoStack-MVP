import asyncio
import sqlite3

# Get the deployment ID from database
conn = sqlite3.connect('autostack.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT d.id, p.repository, d.status, d.created_at 
    FROM deployments d
    JOIN projects p ON d.project_id = p.id
    WHERE p.repository = 'Raj-glitch-max/realtime-chat-hub'
    ORDER BY d.created_at DESC
    LIMIT 1
""")

deployment = cursor.fetchone()
conn.close()

if not deployment:
    print("❌ No deployment found")
    exit(1)

deployment_id = deployment[0]
repository = deployment[1]
status = deployment[2]

print(f"✅ Found deployment:")
print(f"   ID: {deployment_id}")
print(f"   Repository: {repository}")
print(f"   Status: {status}")
print(f"\n🚀 Triggering deployment job...")

# Import and run the deployment job
import uuid
from app.build_engine import run_deployment_job

# Convert string UUID to UUID object
deployment_uuid = uuid.UUID(deployment_id)

# Run the deployment job
asyncio.run(run_deployment_job(deployment_uuid))
