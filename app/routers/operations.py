"""
app/routers/operations.py
─────────────────────────
Inventory operations (Receipts, Deliveries, Internal Transfers, Adjustments).

  POST /              – create operation header
  POST /{id}/lines    – add a product line to an operation
  POST /{id}/validate – atomically validate; triggers inventory engine
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    Location,
    LocationType,
    Operation,
    OperationLine,
    OperationStatus,
    OperationType,
    Product,
    User,
)
from app.schemas import (
    MessageResponse,
    OperationCreate,
    OperationLineCreate,
    OperationLineOut,
    OperationOut,
)
from app.security import get_current_user, require_any_staff, require_manager
from app.services.inventory import (
    InsufficientStockException,
    process_adjustment_line,
    process_operation_line,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["Operations"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_reference(op_type: OperationType) -> str:
    """Generate a human-readable unique reference like RCPT/20240101/ab3f."""
    prefix_map = {
        OperationType.RECEIPT: "RCPT",
        OperationType.DELIVERY: "DLVR",
        OperationType.INTERNAL: "INT",
        OperationType.ADJUSTMENT: "ADJ",
    }
    prefix = prefix_map[op_type]
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_id = uuid.uuid4().hex[:6].upper()
    return f"{prefix}/{date_part}/{short_id}"


async def _load_operation(db: AsyncSession, operation_id: str) -> Operation:
    """Load an operation with all lines eagerly loaded; raise 404 if missing."""
    result = await db.execute(
        select(Operation)
        .options(selectinload(Operation.lines))
        .where(Operation.id == operation_id)
    )
    op: Operation | None = result.scalar_one_or_none()
    if op is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Operation '{operation_id}' not found.",
        )
    return op


async def _get_inventory_loss_location(db: AsyncSession) -> Location:
    """Fetch the Virtual/Inventory-Loss location; raises 500 if missing."""
    result = await db.execute(
        select(Location).where(
            Location.location_type == LocationType.INVENTORY_LOSS
        )
    )
    loc: Location | None = result.scalar_one_or_none()
    if loc is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Virtual/Inventory-Loss location is not seeded. Run seeder.",
        )
    return loc


def _operation_to_out(op: Operation) -> OperationOut:
    """Convert an Operation ORM object to its Pydantic response model."""
    return OperationOut(
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
                id=str(line.id),
                product_id=str(line.product_id),
                quantity=line.quantity,
                source_location_id=str(line.source_location_id),
                dest_location_id=str(line.dest_location_id),
            )
            for line in op.lines
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /operations/
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=OperationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new operation header (DRAFT)",
)
async def create_operation(
    payload: OperationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_staff),
) -> OperationOut:
    """Create a new operation in DRAFT status.  Lines are added separately."""

    # Validate source / dest locations if provided
    for loc_id in filter(None, [payload.source_location_id, payload.dest_location_id]):
        loc_result = await db.execute(
            select(Location).where(Location.id == loc_id, Location.is_active.is_(True))
        )
        if loc_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location '{loc_id}' not found or inactive.",
            )

    operation = Operation(
        reference=_generate_reference(payload.operation_type),
        operation_type=payload.operation_type,
        status=OperationStatus.DRAFT,
        partner_name=payload.partner_name,
        notes=payload.notes,
        source_location_id=payload.source_location_id,
        dest_location_id=payload.dest_location_id,
        created_by_id=str(current_user.id),
    )
    db.add(operation)
    await db.flush()

    # Reload with lines (empty at this point) for serialization
    op = await _load_operation(db, str(operation.id))
    logger.info(
        "Operation created: %s (%s) by %s",
        op.reference,
        op.operation_type,
        current_user.email,
    )
    return _operation_to_out(op)


# ─────────────────────────────────────────────────────────────────────────────
# POST /operations/{id}/lines
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{operation_id}/lines",
    response_model=OperationLineOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a product line to an operation",
)
async def add_operation_line(
    operation_id: str,
    payload: OperationLineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_staff),
) -> OperationLineOut:
    """
    Append a product/qty/location line to an existing operation.
    Only allowed when operation is in DRAFT or WAITING status.
    """
    op = await _load_operation(db, operation_id)

    if op.status not in (OperationStatus.DRAFT, OperationStatus.WAITING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot add lines to operation in status '{op.status.value}'. "
                "Only DRAFT or WAITING operations can be modified."
            ),
        )

    # Validate product
    prod_result = await db.execute(
        select(Product).where(Product.id == payload.product_id, Product.is_active.is_(True))
    )
    if prod_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{payload.product_id}' not found or inactive.",
        )

    # Validate locations
    for loc_id in [payload.source_location_id, payload.dest_location_id]:
        loc_result = await db.execute(
            select(Location).where(Location.id == loc_id, Location.is_active.is_(True))
        )
        if loc_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location '{loc_id}' not found or inactive.",
            )

    line = OperationLine(
        operation_id=operation_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        source_location_id=payload.source_location_id,
        dest_location_id=payload.dest_location_id,
    )
    db.add(line)
    await db.flush()

    return OperationLineOut(
        id=str(line.id),
        product_id=str(line.product_id),
        quantity=line.quantity,
        source_location_id=str(line.source_location_id),
        dest_location_id=str(line.dest_location_id),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /operations/{id}/validate
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{operation_id}/validate",
    response_model=OperationOut,
    summary="Atomically validate operation and execute inventory movements",
)
async def validate_operation(
    operation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_any_staff),
) -> OperationOut:
    """
    Execute the inventory engine inside a single ACID transaction:
    1. Lock StockQuant rows with SELECT FOR UPDATE.
    2. Check sufficient stock (raises 409 on failure → automatic rollback).
    3. Adjust StockQuant balances.
    4. Append immutable StockLedger rows.
    5. Mark operation status = DONE.
    """
    # Load operation outside the engine transaction for existence check
    op = await _load_operation(db, operation_id)

    if op.status == OperationStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operation is already validated (DONE).",
        )
    if op.status == OperationStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot validate a canceled operation.",
        )
    if not op.lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Operation has no lines to process.",
        )

    user_id = str(current_user.id)
    reference = op.reference

    try:
        # ── Single atomic transaction ─────────────────────────────────────────
        async with db.begin_nested():  # savepoint inside the outer session txn
            if op.operation_type == OperationType.ADJUSTMENT:
                loss_location = await _get_inventory_loss_location(db)
                for line in op.lines:
                    # For adjustments: quantity field = the physical count target
                    await process_adjustment_line(
                        db=db,
                        product_id=str(line.product_id),
                        location_id=str(line.dest_location_id),
                        physical_count=line.quantity,
                        inventory_loss_location_id=str(loss_location.id),
                        reference=reference,
                        user_id=user_id,
                    )
            else:
                for line in op.lines:
                    await process_operation_line(
                        db=db,
                        line=line,
                        reference=reference,
                        user_id=user_id,
                    )

            now = datetime.now(timezone.utc)
            op.status = OperationStatus.DONE
            op.validated_at = now
            op.updated_at = now
            await db.flush()

    except InsufficientStockException as exc:
        logger.warning(
            "InsufficientStock during validate op=%s: %s", operation_id, exc
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    # Reload for fresh serialization
    op_refreshed = await _load_operation(db, operation_id)
    logger.info(
        "Operation validated: %s by %s", reference, current_user.email
    )
    return _operation_to_out(op_refreshed)
