"""
app/schemas.py
──────────────
Pydantic v2 request / response schemas for all StockSense endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models import LocationType, OperationStatus, OperationType, UserRole


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    """Base that turns on from_attributes so ORM objects can be serialised."""

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=256)
    role: str = "WAREHOUSE_STAFF"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OtpSendRequest(BaseModel):
    email: str


class OtpVerifyRequest(BaseModel):
    email: str
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

class UserOut(OrmBase):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Category
# ─────────────────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: Optional[str] = None


class CategoryOut(OrmBase):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Product
# ─────────────────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    sku: str = Field(min_length=1, max_length=64)
    uom: str = Field(default="unit", max_length=32)
    min_stock_alert: Decimal = Field(default=Decimal("0"), ge=0)
    category_id: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    sku: Optional[str] = Field(default=None, min_length=1, max_length=64)
    uom: Optional[str] = Field(default=None, max_length=32)
    min_stock_alert: Optional[Decimal] = Field(default=None, ge=0)
    category_id: Optional[str] = None
    is_active: Optional[bool] = None


class StockPerLocation(OrmBase):
    location_id: str
    location_code: str
    quantity: Decimal


class ProductOut(OrmBase):
    id: str
    name: str
    sku: str
    uom: str
    min_stock_alert: Decimal
    category_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    stock_by_location: List[StockPerLocation] = []


class PaginatedProducts(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ProductOut]


# ─────────────────────────────────────────────────────────────────────────────
# Location / Warehouse
# ─────────────────────────────────────────────────────────────────────────────

class WarehouseOut(OrmBase):
    id: str
    name: str
    code: str
    created_at: datetime


class LocationOut(OrmBase):
    id: str
    name: str
    code: str
    location_type: LocationType
    warehouse_id: Optional[str]
    is_active: bool


# ─────────────────────────────────────────────────────────────────────────────
# Operations
# ─────────────────────────────────────────────────────────────────────────────

class OperationCreate(BaseModel):
    operation_type: OperationType
    partner_name: Optional[str] = Field(default=None, max_length=256)
    source_location_id: Optional[str] = None
    dest_location_id: Optional[str] = None
    notes: Optional[str] = None


class OperationLineCreate(BaseModel):
    product_id: str
    quantity: Decimal = Field(gt=0)
    source_location_id: str
    dest_location_id: str


class OperationLineOut(OrmBase):
    id: str
    product_id: str
    quantity: Decimal
    source_location_id: str
    dest_location_id: str


class OperationOut(OrmBase):
    id: str
    reference: str
    operation_type: OperationType
    status: OperationStatus
    partner_name: Optional[str]
    notes: Optional[str]
    source_location_id: Optional[str]
    dest_location_id: Optional[str]
    created_by_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    validated_at: Optional[datetime]
    lines: List[OperationLineOut] = []


# ─────────────────────────────────────────────────────────────────────────────
# Stock Ledger
# ─────────────────────────────────────────────────────────────────────────────

class LedgerEntryOut(BaseModel):
    id: str
    reference: str
    product_id: str
    product_sku: str
    product_name: str
    from_location_id: str
    from_location_code: str
    to_location_id: str
    to_location_code: str
    quantity: Decimal
    user_id: Optional[str]
    user_name: Optional[str]
    created_at: datetime


class PaginatedLedger(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[LedgerEntryOut]


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class DashboardKpis(BaseModel):
    total_products: int
    low_stock_items: int
    out_of_stock_items: int
    pending_receipts: int
    pending_deliveries: int
    scheduled_internal_transfers: int


class FilterRequest(BaseModel):
    operation_type: Optional[OperationType] = None
    status: Optional[OperationStatus] = None
    warehouse_id: Optional[str] = None
    location_id: Optional[str] = None
    category_id: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedOperations(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[OperationOut]


# ─────────────────────────────────────────────────────────────────────────────
# Generic message
# ─────────────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[Any] = None
