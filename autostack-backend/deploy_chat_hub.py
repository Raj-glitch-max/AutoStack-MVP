import asyncio
import uuid
from app.db import AsyncSessionLocal
from app.models import Deployment, Project, User
from sqlalchemy import select
from datetime import datetime

async def create_deployment():
    async with AsyncSessionLocal() as session:
        # Get the first user
        user_result = await session.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            print("❌ No user found. Please create a user first.")
            return
        
        # Check if project exists
        project_result = await session.execute(
            select(Project).where(Project.repository == "Raj-glitch-max/realtime-chat-hub")
        )
        project = project_result.scalar_one_or_none()
        
        if not project:
            # Create project
            project = Project(
                user_id=user.id,
                name="realtime-chat-hub",
                repository="Raj-glitch-max/realtime-chat-hub",
                branch="main",
                runtime="nodejs",
                build_command="npm run build",
                output_dir="dist"
            )
            session.add(project)
            await session.flush()
            print(f"✅ Created project: {project.name}")
        
        # Create deployment
        deployment = Deployment(
            project_id=project.id,
            user_id=user.id,
            status="queued",
            branch="main"
        )
        session.add(deployment)
        await session.commit()
        
        print(f"✅ Successfully created deployment!")
        print(f"   Deployment ID: {deployment.id}")
        print(f"   Project: {project.name}")
        print(f"   Repository: {project.repository}")
        print(f"   Status: {deployment.status}")
        print(f"\n🚀 Starting deployment process...")
        
        # Trigger the deployment
        from app.build_engine import run_deployment_job
        asyncio.create_task(run_deployment_job(deployment.id))
        
        print(f"✅ Deployment job started")
        print(f"   You can view progress at: http://localhost:3000/deployments/{deployment.id}")

if __name__ == '__main__':
    asyncio.run(create_deployment())
