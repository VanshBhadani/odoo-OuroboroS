"""
app/seed.py
───────────
Database initializer & idempotent data seeder.

Can be run directly:
    python -m app.seed

Or called programmatically from the FastAPI lifespan startup hook.

Operations performed (all idempotent – safe to re-run):
  1. Create all tables via SQLAlchemy metadata.
  2. Seed the default Warehouse and all required Locations.
  3. Seed the default product Category ("General").
  4. Seed the default admin user.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, Base, engine
from app.models import Category, Location, LocationType, User, UserRole, Warehouse
from app.security import hash_password

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Table creation
# ─────────────────────────────────────────────────────────────────────────────

async def create_tables() -> None:
    """Create all SQLAlchemy-managed tables if they do not yet exist."""
    async with engine.begin() as conn:
        # Import all models to register their metadata before create_all
        import app.models  # noqa: F401 – ensures all models are registered
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured.")


# ─────────────────────────────────────────────────────────────────────────────
# Individual seeders
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_warehouse(db: AsyncSession) -> Warehouse:
    """Ensure the default warehouse exists; return it."""
    result = await db.execute(
        select(Warehouse).where(Warehouse.code == "WH01")
    )
    warehouse: Warehouse | None = result.scalar_one_or_none()

    if warehouse is None:
        warehouse = Warehouse(
            name="Main Warehouse",
            code="WH01",
            created_at=datetime.now(timezone.utc),
        )
        db.add(warehouse)
        await db.flush()
        logger.info("Seeded warehouse: %s (%s)", warehouse.name, warehouse.code)
    else:
        logger.debug("Warehouse already exists: %s", warehouse.code)

    return warehouse


async def _seed_location(
    db: AsyncSession,
    *,
    name: str,
    code: str,
    location_type: LocationType,
    warehouse: Warehouse | None = None,
) -> Location:
    """Ensure a specific location exists; return it."""
    result = await db.execute(
        select(Location).where(Location.code == code)
    )
    location: Location | None = result.scalar_one_or_none()

    if location is None:
        location = Location(
            name=name,
            code=code,
            location_type=location_type,
            warehouse_id=str(warehouse.id) if warehouse else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(location)
        await db.flush()
        logger.info("Seeded location: %s (%s) [%s]", name, code, location_type.value)
    else:
        logger.debug("Location already exists: %s", code)

    return location


async def _seed_category(db: AsyncSession) -> Category:
    """Ensure the default 'General' category exists; return it."""
    result = await db.execute(
        select(Category).where(Category.name == "General")
    )
    category: Category | None = result.scalar_one_or_none()

    if category is None:
        category = Category(
            name="General",
            description="Default product category",
            created_at=datetime.now(timezone.utc),
        )
        db.add(category)
        await db.flush()
        logger.info("Seeded category: General")
    else:
        logger.debug("Category 'General' already exists.")

    return category


async def _seed_admin(db: AsyncSession) -> User:
    """Ensure the default admin user exists; return it."""
    result = await db.execute(
        select(User).where(User.email == settings.ADMIN_EMAIL.lower())
    )
    admin: User | None = result.scalar_one_or_none()

    if admin is None:
        admin = User(
            email=settings.ADMIN_EMAIL.lower(),
            name=settings.ADMIN_NAME,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            role=UserRole.INVENTORY_MANAGER,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(admin)

        from app.models import AllowlistEmail
        allow_check = await db.execute(select(AllowlistEmail).where(AllowlistEmail.email == settings.ADMIN_EMAIL.lower()))
        if not allow_check.scalars().first():
            db.add(AllowlistEmail(email=settings.ADMIN_EMAIL.lower()))

        await db.flush()
        logger.info(
            "Seeded admin user: %s (role: %s)",
            admin.email,
            admin.role.value,
        )
    else:
        logger.debug("Admin user already exists: %s", settings.ADMIN_EMAIL)

    return admin


# ─────────────────────────────────────────────────────────────────────────────
# Main seed entry point
# ─────────────────────────────────────────────────────────────────────────────

async def run_seed() -> None:
    """
    Idempotent seed runner.  Safe to call on every application startup.
    All operations are wrapped in a single transaction so a partial failure
    rolls back cleanly.
    """
    await create_tables()

    async with AsyncSessionLocal() as db:
        async with db.begin():
            # 1. Warehouse
            warehouse = await _seed_warehouse(db)

            # 2. Locations
            await _seed_location(
                db,
                name="WH01/Stock",
                code="WH01/Stock",
                location_type=LocationType.INTERNAL,
                warehouse=warehouse,
            )
            await _seed_location(
                db,
                name="Virtual/Vendor",
                code="Virtual/Vendor",
                location_type=LocationType.VENDOR,
            )
            await _seed_location(
                db,
                name="Virtual/Customer",
                code="Virtual/Customer",
                location_type=LocationType.CUSTOMER,
            )
            await _seed_location(
                db,
                name="Virtual/Inventory-Loss",
                code="Virtual/Inventory-Loss",
                location_type=LocationType.INVENTORY_LOSS,
            )

            # 3. Default category
            await _seed_category(db)

            # 4. Admin user
            await _seed_admin(db)

    logger.info("Database seeding complete.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_seed())
