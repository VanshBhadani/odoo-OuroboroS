import asyncio
from app.database import AsyncSessionLocal
from app.models import User
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User))
        for u in res.scalars():
            print(f"Email: {u.email}, Role: {u.role}")

asyncio.run(main())
