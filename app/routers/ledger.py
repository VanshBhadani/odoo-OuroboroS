"""
app/routers/ledger.py
─────────────────────
Read-only stock ledger audit log.

  GET /moves  – paginated ledger entries with enriched join metadata
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database import get_db
from app.models import Location, Product, StockLedger, User
from app.schemas import LedgerEntryOut, PaginatedLedger
from app.security import require_any_staff

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ledger", tags=["Ledger"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /ledger/moves
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/moves",
    response_model=PaginatedLedger,
    summary="Paginated, read-only stock movement audit log",
)
async def list_ledger_moves(
    product_id: Optional[str] = Query(default=None, description="Filter by product UUID"),
    location_id: Optional[str] = Query(
        default=None, description="Filter by source or destination location UUID"
    ),
    reference: Optional[str] = Query(
        default=None, description="Filter by operation reference (partial match)"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_staff),
) -> PaginatedLedger:
    """
    Returns a paginated audit trail of all stock movements with enriched
    metadata: product SKU/name, location codes, and user name.
    Strictly read-only – no mutations possible via this endpoint.
    """

    # ── Aliases for joined tables ─────────────────────────────────────────────
    FromLoc = aliased(Location, name="from_location")
    ToLoc = aliased(Location, name="to_location")

    # ── Base query ────────────────────────────────────────────────────────────
    stmt = (
        select(StockLedger, Product, FromLoc, ToLoc, User)
        .join(Product, Product.id == StockLedger.product_id)
        .join(FromLoc, FromLoc.id == StockLedger.from_location_id)
        .join(ToLoc, ToLoc.id == StockLedger.to_location_id)
        .outerjoin(User, User.id == StockLedger.user_id)
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    if product_id is not None:
        stmt = stmt.where(StockLedger.product_id == product_id)

    if location_id is not None:
        stmt = stmt.where(
            (StockLedger.from_location_id == location_id)
            | (StockLedger.to_location_id == location_id)
        )

    if reference is not None:
        stmt = stmt.where(StockLedger.reference.ilike(f"%{reference}%"))

    # ── Count ─────────────────────────────────────────────────────────────────
    count_result = await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total: int = count_result.scalar_one()

    # ── Paginate (newest first) ───────────────────────────────────────────────
    stmt = (
        stmt.order_by(StockLedger.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    rows = result.all()

    items: list[LedgerEntryOut] = []
    for ledger, product, from_loc, to_loc, user in rows:
        items.append(
            LedgerEntryOut(
                id=str(ledger.id),
                reference=ledger.reference,
                product_id=str(ledger.product_id),
                product_sku=product.sku,
                product_name=product.name,
                from_location_id=str(ledger.from_location_id),
                from_location_code=from_loc.code,
                to_location_id=str(ledger.to_location_id),
                to_location_code=to_loc.code,
                quantity=Decimal(str(ledger.quantity)),
                user_id=str(ledger.user_id) if ledger.user_id else None,
                user_name=user.name if user else None,
                created_at=ledger.created_at,
            )
        )

    return PaginatedLedger(total=total, page=page, page_size=page_size, items=items)
