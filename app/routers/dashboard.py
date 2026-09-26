"""
app/routers/dashboard.py
────────────────────────
Dashboard endpoints providing aggregate KPIs and dynamic operation filtering.

  GET /kpis   – aggregate counts for the dashboard summary cards
  GET /filter – dynamic search / filter across operations
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Location,
    Operation,
    OperationStatus,
    OperationType,
    Product,
    StockQuant,
    User,
)
from app.schemas import (
    DashboardKpis,
    FilterRequest,
    OperationLineOut,
    OperationOut,
    PaginatedOperations,
)
from app.security import require_any_staff

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /dashboard/kpis
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/kpis",
    response_model=DashboardKpis,
    summary="Aggregate KPI counts for the dashboard",
)
async def get_kpis(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_staff),
) -> DashboardKpis:
    """
    Executes efficient aggregate SQL queries to return:
    - Total active products
    - Low-stock items (total_qty <= min_stock_alert, but > 0)
    - Out-of-stock items (total_qty == 0 for active products)
    - Pending receipts (WAITING or READY)
    - Pending deliveries (WAITING or READY)
    - Scheduled internal transfers (DRAFT, WAITING, or READY)
    """

    # ── Total active products ─────────────────────────────────────────────────
    total_products_result = await db.execute(
        select(func.count(Product.id)).where(Product.is_active.is_(True))
    )
    total_products: int = total_products_result.scalar_one()

    # ── Per-product total stock (sum across all internal locations) ───────────
    # Subquery: total stock per product from StockQuant
    stock_subq = (
        select(
            StockQuant.product_id.label("product_id"),
            func.sum(StockQuant.quantity).label("total_qty"),
        )
        .join(Location, Location.id == StockQuant.location_id)
        .where(Location.location_type == "INTERNAL")
        .group_by(StockQuant.product_id)
        .subquery()
    )

    # Low stock: total_qty > 0 AND total_qty <= min_stock_alert
    low_stock_result = await db.execute(
        select(func.count(Product.id))
        .join(stock_subq, stock_subq.c.product_id == Product.id)
        .where(
            Product.is_active.is_(True),
            stock_subq.c.total_qty > 0,
            stock_subq.c.total_qty <= Product.min_stock_alert,
        )
    )
    low_stock_items: int = low_stock_result.scalar_one()

    # Out of stock: active products with total_qty == 0 (or no quant row)
    out_of_stock_result = await db.execute(
        select(func.count(Product.id))
        .outerjoin(stock_subq, stock_subq.c.product_id == Product.id)
        .where(
            Product.is_active.is_(True),
            or_(
                stock_subq.c.total_qty.is_(None),
                stock_subq.c.total_qty == 0,
            ),
        )
    )
    out_of_stock_items: int = out_of_stock_result.scalar_one()

    # ── Pending receipts ──────────────────────────────────────────────────────
    pending_receipts_result = await db.execute(
        select(func.count(Operation.id)).where(
            Operation.operation_type == OperationType.RECEIPT,
            Operation.status.in_([OperationStatus.WAITING, OperationStatus.READY]),
        )
    )
    pending_receipts: int = pending_receipts_result.scalar_one()

    # ── Pending deliveries ────────────────────────────────────────────────────
    pending_deliveries_result = await db.execute(
        select(func.count(Operation.id)).where(
            Operation.operation_type == OperationType.DELIVERY,
            Operation.status.in_([OperationStatus.WAITING, OperationStatus.READY]),
        )
    )
    pending_deliveries: int = pending_deliveries_result.scalar_one()

    # ── Scheduled internal transfers ──────────────────────────────────────────
    scheduled_internal_result = await db.execute(
        select(func.count(Operation.id)).where(
            Operation.operation_type == OperationType.INTERNAL,
            Operation.status.in_(
                [OperationStatus.DRAFT, OperationStatus.WAITING, OperationStatus.READY]
            ),
        )
    )
    scheduled_internal: int = scheduled_internal_result.scalar_one()

    return DashboardKpis(
        total_products=total_products,
        low_stock_items=low_stock_items,
        out_of_stock_items=out_of_stock_items,
        pending_receipts=pending_receipts,
        pending_deliveries=pending_deliveries,
        scheduled_internal_transfers=scheduled_internal,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /dashboard/filter
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/filter",
    response_model=PaginatedOperations,
    summary="Dynamically filter operations by type, status, warehouse, location, or category",
)
async def filter_operations(
    operation_type: Optional[OperationType] = Query(default=None),
    status: Optional[OperationStatus] = Query(default=None),
    warehouse_id: Optional[str] = Query(default=None),
    location_id: Optional[str] = Query(default=None),
    category_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_staff),
) -> PaginatedOperations:
    """
    Flexible filter endpoint that applies all supplied query parameters as AND
    conditions against the operations table.  Supports pagination.
    """
    conditions = []

    if operation_type is not None:
        conditions.append(Operation.operation_type == operation_type)
    if status is not None:
        conditions.append(Operation.status == status)

    # Filter by source or dest location
    if location_id is not None:
        conditions.append(
            or_(
                Operation.source_location_id == location_id,
                Operation.dest_location_id == location_id,
            )
        )

    # Filter by warehouse: match locations belonging to the warehouse
    if warehouse_id is not None and location_id is None:
        loc_subq = (
            select(Location.id)
            .where(Location.warehouse_id == warehouse_id)
            .scalar_subquery()
        )
        conditions.append(
            or_(
                Operation.source_location_id.in_(loc_subq),
                Operation.dest_location_id.in_(loc_subq),
            )
        )

    # Filter by category: match operations that have lines with products in that category
    if category_id is not None:
        from app.models import OperationLine, Product as PModel
        cat_op_subq = (
            select(OperationLine.operation_id)
            .join(PModel, PModel.id == OperationLine.product_id)
            .where(PModel.category_id == category_id)
            .distinct()
            .scalar_subquery()
        )
        conditions.append(Operation.id.in_(cat_op_subq))

    base_stmt = select(Operation).where(and_(*conditions) if conditions else True)

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(base_stmt.subquery())
    )
    total: int = count_result.scalar_one()

    # Paginate + eager-load lines
    stmt = (
        base_stmt.options(selectinload(Operation.lines))
        .order_by(Operation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    operations = result.scalars().all()

    items = [
        OperationOut(
            id=str(op.id),
            reference=op.reference,
            operation_type=op.operation_type,
            status=op.status,
            partner_name=op.partner_name,
            notes=op.notes,
            source_location_id=str(op.source_location_id) if op.source_location_id else None,
            dest_location_id=str(op.dest_location_id) if op.dest_location_id else None,
            created_by_id=str(op.created_by_id) if op.created_by_id else None,
            created_at=op.created_at,
            updated_at=op.updated_at,
            validated_at=op.validated_at,
            lines=[
                OperationLineOut(
                    id=str(ln.id),
                    product_id=str(ln.product_id),
                    quantity=ln.quantity,
                    source_location_id=str(ln.source_location_id),
                    dest_location_id=str(ln.dest_location_id),
                )
                for ln in op.lines
            ],
        )
        for op in operations
    ]

    return PaginatedOperations(total=total, page=page, page_size=page_size, items=items)
