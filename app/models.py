"""
app/models.py
─────────────
SQLAlchemy 2.0 ORM models for StockSense.

Table dependency order (create_all-safe):
  Category → Product
  Warehouse → Location → StockQuant
  User → OtpVerification
  Operation → OperationLine
  StockLedger
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _uuid() -> str:
    """Return a new UUID4 as a string (used as server-side default callable)."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    INVENTORY_MANAGER = "INVENTORY_MANAGER"
    WAREHOUSE_STAFF = "WAREHOUSE_STAFF"


class LocationType(str, enum.Enum):
    INTERNAL = "INTERNAL"
    VENDOR = "VENDOR"
    CUSTOMER = "CUSTOMER"
    INVENTORY_LOSS = "INVENTORY_LOSS"


class OperationType(str, enum.Enum):
    RECEIPT = "RECEIPT"
    DELIVERY = "DELIVERY"
    INTERNAL = "INTERNAL"
    ADJUSTMENT = "ADJUSTMENT"


class OperationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    WAITING = "WAITING"
    READY = "READY"
    DONE = "DONE"
    CANCELED = "CANCELED"


# ─────────────────────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────────────────────

class Category(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    products = relationship("Product", back_populates="category")


# ─────────────────────────────────────────────────────────────────────────────
# Product
# ─────────────────────────────────────────────────────────────────────────────

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(256), nullable=False)
    sku = Column(String(64), nullable=False, unique=True, index=True)
    uom = Column(String(32), nullable=False, default="unit")
    min_stock_alert = Column(Numeric(12, 4), nullable=False, default=0)
    category_id = Column(
        UUID(as_uuid=False),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    category = relationship("Category", back_populates="products")
    stock_quants = relationship("StockQuant", back_populates="product")
    ledger_entries = relationship(
        "StockLedger",
        back_populates="product",
        foreign_keys="StockLedger.product_id",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Warehouse
# ─────────────────────────────────────────────────────────────────────────────

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(256), nullable=False)
    code = Column(String(16), nullable=False, unique=True, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    locations = relationship("Location", back_populates="warehouse")


# ─────────────────────────────────────────────────────────────────────────────
# Location
# ─────────────────────────────────────────────────────────────────────────────

class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(256), nullable=False)
    code = Column(String(64), nullable=False, unique=True, index=True)
    location_type = Column(
        Enum(LocationType, name="location_type_enum"),
        nullable=False,
        default=LocationType.INTERNAL,
    )
    warehouse_id = Column(
        UUID(as_uuid=False),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    warehouse = relationship("Warehouse", back_populates="locations")
    stock_quants = relationship("StockQuant", back_populates="location")


# ─────────────────────────────────────────────────────────────────────────────
# StockQuant  (materialized balance ledger)
# ─────────────────────────────────────────────────────────────────────────────

class StockQuant(Base):
    __tablename__ = "stock_quants"
    __table_args__ = (
        UniqueConstraint("product_id", "location_id", name="uq_product_location"),
        CheckConstraint("quantity >= 0", name="ck_quant_non_negative"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    product_id = Column(
        UUID(as_uuid=False),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity = Column(Numeric(12, 4), nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    product = relationship("Product", back_populates="stock_quants")
    location = relationship("Location", back_populates="stock_quants")


# ─────────────────────────────────────────────────────────────────────────────
# SystemSetting (Key-Value pairs for config)
# ─────────────────────────────────────────────────────────────────────────────

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    key = Column(String(64), primary_key=True)
    value = Column(String(256), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email = Column(String(256), nullable=False, unique=True, index=True)
    name = Column(String(256), nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(256), nullable=False, default="WAREHOUSE_STAFF")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    otp_verifications = relationship(
        "OtpVerification", back_populates="user", cascade="all, delete-orphan"
    )
    ledger_entries = relationship(
        "StockLedger",
        back_populates="actor",
        foreign_keys="StockLedger.user_id",
    )
    operations = relationship("Operation", back_populates="created_by")


# ─────────────────────────────────────────────────────────────────────────────
# Allowlist Email
# ─────────────────────────────────────────────────────────────────────────────

class AllowlistEmail(Base):
    __tablename__ = "allowlist_emails"

    email = Column(String(256), primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


# ─────────────────────────────────────────────────────────────────────────────
# OTP Verification
# ─────────────────────────────────────────────────────────────────────────────

class OtpVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email = Column(String(256), nullable=False, index=True)
    otp_hash = Column(String(256), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    is_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # optional FK – OTP may be requested before a user account exists; kept nullable
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user = relationship("User", back_populates="otp_verifications")


# ─────────────────────────────────────────────────────────────────────────────
# Operation (header)
# ─────────────────────────────────────────────────────────────────────────────

class Operation(Base):
    __tablename__ = "operations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    reference = Column(String(64), nullable=False, unique=True, index=True)
    operation_type = Column(
        Enum(OperationType, name="operation_type_enum"), nullable=False
    )
    status = Column(
        Enum(OperationStatus, name="operation_status_enum"),
        nullable=False,
        default=OperationStatus.DRAFT,
    )
    partner_name = Column(String(256), nullable=True)
    notes = Column(Text, nullable=True)

    # Default source / destination for the entire operation (can be overridden per line)
    source_location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    dest_location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
    )

    created_by_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    validated_at = Column(DateTime(timezone=True), nullable=True)

    lines = relationship(
        "OperationLine", back_populates="operation", cascade="all, delete-orphan"
    )
    created_by = relationship("User", back_populates="operations")
    source_location = relationship("Location", foreign_keys=[source_location_id])
    dest_location = relationship("Location", foreign_keys=[dest_location_id])


# ─────────────────────────────────────────────────────────────────────────────
# Operation Line (detail rows)
# ─────────────────────────────────────────────────────────────────────────────

class OperationLine(Base):
    __tablename__ = "operation_lines"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    operation_id = Column(
        UUID(as_uuid=False),
        ForeignKey("operations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        UUID(as_uuid=False),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity = Column(Numeric(12, 4), nullable=False)
    source_location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dest_location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
    )

    operation = relationship("Operation", back_populates="lines")
    product = relationship("Product")
    source_location = relationship("Location", foreign_keys=[source_location_id])
    dest_location = relationship("Location", foreign_keys=[dest_location_id])


# ─────────────────────────────────────────────────────────────────────────────
# StockLedger  (immutable audit log – append-only)
# ─────────────────────────────────────────────────────────────────────────────

class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    reference = Column(String(64), nullable=False, index=True)
    product_id = Column(
        UUID(as_uuid=False),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    from_location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_location_id = Column(
        UUID(as_uuid=False),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity = Column(Numeric(12, 4), nullable=False)
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    product = relationship(
        "Product", back_populates="ledger_entries", foreign_keys=[product_id]
    )
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])
    actor = relationship(
        "User", back_populates="ledger_entries", foreign_keys=[user_id]
    )
