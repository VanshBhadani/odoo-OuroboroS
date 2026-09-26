"""
app/services/inventory.py
─────────────────────────
Core inventory engine – the ONLY place that touches StockQuant and StockLedger.

All public functions must be called from within an active database transaction
(`async with db.begin():`).  This module never starts or commits transactions
itself; that responsibility belongs to the router / caller.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Location,
    LocationType,
    OperationLine,
    OperationType,
    StockLedger,
    StockQuant,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Custom exceptions
# ─────────────────────────────────────────────────────────────────────────────

class InsufficientStockException(Exception):
    """Raised when available stock is less than the requested quantity."""

    def __init__(self, product_id: str, location_id: str, available: Decimal, requested: Decimal):
        self.product_id = product_id
        self.location_id = location_id
        self.available = available
        self.requested = requested
        super().__init__(
            f"Insufficient stock for product {product_id} at location {location_id}: "
            f"available={available}, requested={requested}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_or_create_quant(
    db: AsyncSession,
    product_id: str,
    location_id: str,
    lock: bool = False,
) -> StockQuant:
    """
    Return the StockQuant row for (product, location), creating one with qty=0
    if it does not yet exist.

    When *lock* is True the row is locked with SELECT … FOR UPDATE to prevent
    concurrent modifications (ACID requirement).
    """
    stmt = select(StockQuant).where(
        StockQuant.product_id == product_id,
        StockQuant.location_id == location_id,
    )
    if lock:
        stmt = stmt.with_for_update()

    result = await db.execute(stmt)
    quant: Optional[StockQuant] = result.scalar_one_or_none()

    if quant is None:
        quant = StockQuant(
            product_id=product_id,
            location_id=location_id,
            quantity=Decimal("0"),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(quant)
        await db.flush()  # assign PK without committing
    return quant


async def _is_virtual_location(db: AsyncSession, location_id: str) -> bool:
    """Return True when the location is a non-INTERNAL (virtual) type."""
    result = await db.execute(
        select(Location.location_type).where(Location.id == location_id)
    )
    loc_type = result.scalar_one_or_none()
    return loc_type != LocationType.INTERNAL


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def process_operation_line(
    db: AsyncSession,
    line: OperationLine,
    reference: str,
    user_id: Optional[str],
) -> None:
    """
    Apply one double-entry stock movement for *line*.

    Rules
    -----
    * Source virtual location  → always has unlimited stock (skip debit check).
    * Source internal location → lock quant, check sufficiency, debit.
    * Dest virtual location    → skip credit (no need to track virtual balances).
    * Dest internal location   → credit quant.

    A StockLedger entry is always appended regardless of location types.
    """
    product_id = str(line.product_id)
    src_id = str(line.source_location_id)
    dst_id = str(line.dest_location_id)
    qty = Decimal(str(line.quantity))

    src_virtual = await _is_virtual_location(db, src_id)
    dst_virtual = await _is_virtual_location(db, dst_id)

    # ── Debit source (only for internal locations) ────────────────────────────
    if not src_virtual:
        src_quant = await _get_or_create_quant(db, product_id, src_id, lock=True)
        available = Decimal(str(src_quant.quantity))
        if available < qty:
            raise InsufficientStockException(product_id, src_id, available, qty)
        src_quant.quantity = available - qty
        src_quant.updated_at = datetime.now(timezone.utc)

    # ── Credit destination (only for internal locations) ─────────────────────
    if not dst_virtual:
        dst_quant = await _get_or_create_quant(db, product_id, dst_id, lock=True)
        dst_quant.quantity = Decimal(str(dst_quant.quantity)) + qty
        dst_quant.updated_at = datetime.now(timezone.utc)

    # ── Append immutable ledger entry ─────────────────────────────────────────
    ledger_entry = StockLedger(
        reference=reference,
        product_id=product_id,
        from_location_id=src_id,
        to_location_id=dst_id,
        quantity=qty,
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(ledger_entry)
    logger.info(
        "StockLedger | ref=%s | product=%s | %s -> %s | qty=%s",
        reference,
        product_id,
        src_id,
        dst_id,
        qty,
    )


async def process_adjustment_line(
    db: AsyncSession,
    product_id: str,
    location_id: str,
    physical_count: Decimal,
    inventory_loss_location_id: str,
    reference: str,
    user_id: Optional[str],
) -> None:
    """
    Handle a stock adjustment (physical inventory count correction).

    * physical > system  → Virtual/Inventory-Loss → Internal  (GAIN)
    * physical < system  → Internal → Virtual/Inventory-Loss   (LOSS)
    * physical == system → no-op
    """
    quant = await _get_or_create_quant(db, product_id, location_id, lock=True)
    system_qty = Decimal(str(quant.quantity))
    diff = physical_count - system_qty

    if diff == Decimal("0"):
        logger.info(
            "Adjustment no-op for product=%s at location=%s (no change)",
            product_id,
            location_id,
        )
        return

    if diff > 0:
        # Gain: virtual loss → internal
        src_id = inventory_loss_location_id
        dst_id = location_id
        quant.quantity = system_qty + diff
    else:
        # Loss: internal → virtual loss
        src_id = location_id
        dst_id = inventory_loss_location_id
        if system_qty + diff < Decimal("0"):
            raise InsufficientStockException(
                product_id, location_id, system_qty, abs(diff)
            )
        quant.quantity = system_qty + diff  # diff is negative

    quant.updated_at = datetime.now(timezone.utc)

    ledger_entry = StockLedger(
        reference=reference,
        product_id=product_id,
        from_location_id=src_id,
        to_location_id=dst_id,
        quantity=abs(diff),
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(ledger_entry)
    logger.info(
        "StockAdjustment | ref=%s | product=%s | diff=%s | %s -> %s",
        reference,
        product_id,
        diff,
        src_id,
        dst_id,
    )
