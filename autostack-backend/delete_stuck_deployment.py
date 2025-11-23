import asyncio
import uuid
from app.db import AsyncSessionLocal
from app.models import Deployment
from sqlalchemy import update

async def delete_deployment():
    deployment_id = uuid.UUID('ed78c921-5759-4866-90b0-b2b02e407cc4')
    
    async with AsyncSessionLocal() as session:
        # Mark deployment as deleted and cancelled
        result = await session.execute(
            update(Deployment)
            .where(Deployment.id == deployment_id)
            .values(is_deleted=True, status='cancelled')
        )
        await session.commit()
        print(f'✅ Successfully deleted deployment {deployment_id}')

if __name__ == '__main__':
    asyncio.run(delete_deployment())
