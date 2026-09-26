from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict

from app.database import get_db
from app.models import User, SystemSetting, Warehouse, Location, LocationType
from app.security import require_manager, require_any_staff
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

class SettingUpdate(BaseModel):
    key: str
    value: str

class LocationCreate(BaseModel):
    name: str
    code: str
    warehouse_id: str

@router.get("/company")
async def get_company_setting(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SystemSetting).where(SystemSetting.key == "company_name"))
    setting = res.scalars().first()
    return {"company_name": setting.value if setting else "StockSense Inc."}

@router.post("/company")
async def update_company_setting(
    payload: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    if payload.key != "company_name":
        raise HTTPException(status_code=400, detail="Only company_name is supported here")
    
    res = await db.execute(select(SystemSetting).where(SystemSetting.key == "company_name"))
    setting = res.scalars().first()
    if setting:
        setting.value = payload.value
    else:
        setting = SystemSetting(key="company_name", value=payload.value)
        db.add(setting)
    
    await db.commit()
    return {"message": "Updated"}

@router.post("/locations")
async def create_location(
    payload: LocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    res = await db.execute(select(Location).where(Location.code == payload.code))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Location code already exists")
    
    loc = Location(
        name=payload.name,
        code=payload.code,
        warehouse_id=payload.warehouse_id,
        location_type=LocationType.INTERNAL
    )
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return loc

@router.get("/warehouses")
async def get_warehouses(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Warehouse))
    warehouses = res.scalars().all()
    return [{"id": str(w.id), "name": w.name, "code": w.code} for w in warehouses]

@router.post("/warehouses")
async def create_warehouse(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    name = payload.get("name")
    code = payload.get("code")
    res = await db.execute(select(Warehouse).where(Warehouse.code == code))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Warehouse code already exists")
        
    wh = Warehouse(name=name, code=code)
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return {"id": str(wh.id), "name": wh.name, "code": wh.code}

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    from app.models import Category
    res = await db.execute(select(Category))
    categories = res.scalars().all()
    return [{"id": str(c.id), "name": c.name, "description": c.description} for c in categories]

@router.post("/categories")
async def create_category(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    from app.models import Category
    name = payload.get("name")
    desc = payload.get("description", "")
    res = await db.execute(select(Category).where(Category.name == name))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Category name already exists")
        
    cat = Category(name=name, description=desc)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"id": str(cat.id), "name": cat.name, "description": cat.description}

@router.get("/members")
async def get_members(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_manager)):
    from app.models import AllowlistEmail
    res = await db.execute(select(AllowlistEmail))
    members = res.scalars().all()
    return [{"email": m.email, "created_at": m.created_at} for m in members]

@router.post("/members")
async def add_member(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    from app.models import AllowlistEmail
    email = payload.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    res = await db.execute(select(AllowlistEmail).where(AllowlistEmail.email == email))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Email is already in the allowlist")
        
    member = AllowlistEmail(email=email)
    db.add(member)
    await db.commit()
    return {"email": member.email}

@router.delete("/members/{email}")
async def remove_member(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    from app.models import AllowlistEmail
    # Prevent deleting own email or admin email (optional but good practice)
    from app.config import settings
    if email.lower() == settings.ADMIN_EMAIL.lower() or email.lower() == current_user.email.lower():
        raise HTTPException(status_code=400, detail="Cannot remove admin or yourself")
        
    res = await db.execute(select(AllowlistEmail).where(AllowlistEmail.email == email.lower()))
    member = res.scalars().first()
    if not member:
        raise HTTPException(status_code=404, detail="Email not found in allowlist")
        
    await db.delete(member)
    await db.commit()
    return {"message": "Member removed"}
