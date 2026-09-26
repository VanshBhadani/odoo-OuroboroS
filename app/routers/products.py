"""
app/routers/products.py
───────────────────────
Products CRUD with paginated listing, category filtering, SKU/name search,
and per-location stock aggregation.

  GET  /            – paginated product list
  POST /            – create product
  PUT  /{id}        – update product metadata / alert threshold
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Category, Location, Product, StockQuant, User
from app.schemas import (
    PaginatedProducts,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    StockPerLocation,
)
from app.security import get_current_user, require_any_staff, require_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _build_product_out(db: AsyncSession, product: Product) -> ProductOut:
    """Attach aggregated per-location stock to a product ORM instance."""
    quant_result = await db.execute(
        select(StockQuant, Location)
        .join(Location, Location.id == StockQuant.location_id)
        .where(StockQuant.product_id == str(product.id))
    )
    rows = quant_result.all()

    stock_by_location = [
        StockPerLocation(
            location_id=str(loc.id),
            location_code=loc.code,
            quantity=Decimal(str(sq.quantity)),
        )
        for sq, loc in rows
    ]

    p_dict = {
        "id": str(product.id),
        "name": product.name,
        "sku": product.sku,
        "uom": product.uom,
        "min_stock_alert": Decimal(str(product.min_stock_alert)),
        "category_id": str(product.category_id) if product.category_id else None,
        "is_active": product.is_active,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "stock_by_location": stock_by_location,
    }
    return ProductOut(**p_dict)


# ─────────────────────────────────────────────────────────────────────────────
# GET /products/
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=PaginatedProducts,
    summary="Paginated product list with optional search and category filter",
)
async def list_products(
    search: Optional[str] = Query(default=None, description="Search by SKU or name"),
    category_id: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_staff),
) -> PaginatedProducts:
    """Return a paginated list of products with aggregated stock per location."""

    stmt = select(Product)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Product.name.ilike(pattern) | Product.sku.ilike(pattern)
        )
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)

    # Count total for pagination metadata
    count_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total: int = count_result.scalar_one()

    # Paginate
    stmt = stmt.order_by(Product.name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    products = result.scalars().all()

    items = [await _build_product_out(db, p) for p in products]

    return PaginatedProducts(total=total, page=page, page_size=page_size, items=items)


# ─────────────────────────────────────────────────────────────────────────────
# POST /products/
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager),
) -> ProductOut:
    """Create a product.  SKU must be unique.  Requires INVENTORY_MANAGER role."""

    # Check unique SKU
    existing = await db.execute(
        select(Product).where(Product.sku == payload.sku)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A product with SKU '{payload.sku}' already exists.",
        )

    # Validate category if provided
    if payload.category_id:
        cat_result = await db.execute(
            select(Category).where(Category.id == payload.category_id)
        )
        if cat_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{payload.category_id}' not found.",
            )

    product = Product(
        name=payload.name,
        sku=payload.sku,
        uom=payload.uom,
        min_stock_alert=payload.min_stock_alert,
        category_id=payload.category_id,
    )
    db.add(product)
    await db.flush()
    logger.info("Product created: %s (%s) by %s", product.name, product.sku, current_user.email)
    return await _build_product_out(db, product)


# ─────────────────────────────────────────────────────────────────────────────
# PUT /products/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.put(
    "/{product_id}",
    response_model=ProductOut,
    summary="Update product metadata and reordering thresholds",
)
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager),
) -> ProductOut:
    """Update an existing product.  Requires INVENTORY_MANAGER role."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product: Product | None = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found.",
        )

    if payload.name is not None:
        product.name = payload.name
    if payload.sku is not None and payload.sku != product.sku:
        existing = await db.execute(select(Product).where(Product.sku == payload.sku))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A product with SKU '{payload.sku}' already exists.")
        product.sku = payload.sku
    if payload.uom is not None:
        product.uom = payload.uom
    if payload.min_stock_alert is not None:
        product.min_stock_alert = payload.min_stock_alert
    if payload.is_active is not None:
        product.is_active = payload.is_active
    if payload.category_id is not None:
        cat_result = await db.execute(
            select(Category).where(Category.id == payload.category_id)
        )
        if cat_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{payload.category_id}' not found.",
            )
        product.category_id = payload.category_id

    await db.flush()
    logger.info("Product updated: %s by %s", product_id, current_user.email)
    return await _build_product_out(db, product)
