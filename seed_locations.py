import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from app.models import Location, Warehouse, LocationType

async def seed_locations():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/stocksense_db')
    async with AsyncSession(engine) as session:
        # Get the first warehouse
        res = await session.execute(select(Warehouse))
        wh = res.scalars().first()
        if not wh:
            print("No warehouse found!")
            return

        locations_to_add = [
            ("Main Receiving Dock", "WH01/Dock"),
            ("Quality Assurance", "WH01/QA"),
            ("Cold Storage", "WH01/Cold"),
            ("High Value Cage", "WH01/Secure"),
            ("Aisle 1 - Racks A-D", "WH01/Rack-A1"),
            ("Aisle 2 - Racks E-H", "WH01/Rack-A2"),
            ("Packing Area", "WH01/Packing")
        ]

        for name, code in locations_to_add:
            # Check if exists
            exists = await session.execute(select(Location).where(Location.code == code))
            if not exists.scalars().first():
                loc = Location(
                    name=name,
                    code=code,
                    location_type=LocationType.INTERNAL,
                    warehouse_id=wh.id
                )
                session.add(loc)
        
        await session.commit()
        print("Successfully seeded 7 internal locations!")

asyncio.run(seed_locations())
