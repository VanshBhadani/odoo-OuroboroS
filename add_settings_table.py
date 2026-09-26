import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base
from app.models import SystemSetting

async def run():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/stocksense_db')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Created system_settings table")

asyncio.run(run())
