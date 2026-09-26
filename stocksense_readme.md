# StockSense – Backend Implementation Summary

## Files Written (15 total)

| # | File | Purpose |
|---|------|---------|
| 1 | [`requirements.txt`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/requirements.txt) | Pinned deps for Python 3.10+ |
| 2 | [`.env.example`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/.env.example) | Local PostgreSQL config template |
| 3 | [`app/config.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/config.py) | Pydantic-settings singleton |
| 4 | [`app/database.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/database.py) | Async engine + session + `get_db` dep |
| 5 | [`app/models.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/models.py) | All ORM models + enums |
| 6 | [`app/schemas.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/schemas.py) | Pydantic v2 request/response schemas |
| 7 | [`app/security.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/security.py) | bcrypt + JWT + RBAC dependencies |
| 8 | [`app/services/inventory.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/services/inventory.py) | **Core double-entry engine** |
| 9 | [`app/routers/auth.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/routers/auth.py) | signup / login / OTP send+verify |
| 10 | [`app/routers/products.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/routers/products.py) | Paginated CRUD + stock aggregation |
| 11 | [`app/routers/operations.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/routers/operations.py) | Create / add lines / validate (ACID) |
| 12 | [`app/routers/dashboard.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/routers/dashboard.py) | KPI aggregates + dynamic filter |
| 13 | [`app/routers/ledger.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/routers/ledger.py) | Read-only audit log |
| 14 | [`app/seed.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/app/seed.py) | Idempotent seeder + CLI entry |
| 15 | [`main.py`](file:///c:/Users/aeshi/Desktop/StockSense/odoo-OuroboroS/main.py) | FastAPI app, lifespan, routers |

---

## Quick Start

```powershell
# 1. Create your .env
Copy-Item .env.example .env   # then edit DATABASE_URL, SECRET_KEY

# 2. Create the PostgreSQL database
psql -U postgres -c "CREATE DATABASE stocksense_db;"

# 3. Install dependencies (Python 3.10+)
pip install -r requirements.txt

# 4. Run the server (tables created + seeded automatically on startup)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Architecture Decisions

### Double-Entry Ledger
Every stock change moves quantity **between** two locations:

| Operation | Source → Destination |
|-----------|----------------------|
| Receipt | `Virtual/Vendor` → `WH01/Stock` |
| Delivery | `WH01/Stock` → `Virtual/Customer` |
| Internal Transfer | `Internal A` → `Internal B` |
| Adjustment (gain) | `Virtual/Inventory-Loss` → `Internal` |
| Adjustment (loss) | `Internal` → `Virtual/Inventory-Loss` |

### ACID & Concurrency
- `validate` endpoint uses `db.begin_nested()` (savepoint) inside the outer session.
- `StockQuant` rows are locked via `.with_for_update()` before any read-then-write.
- `InsufficientStockException` triggers automatic savepoint rollback.

### PostgreSQL-Native OTP (No Redis)
- Stored in `otp_verifications` table with `expires_at` (indexed).
- Cooldown enforced via SQL: `created_at > NOW() - interval '60 seconds'`.
- Brute-force protection: `attempts` column incremented on failure; locked at ≥ 3.

### RBAC
Two roles enforced via reusable `Depends()` factories:
- `require_manager` → `INVENTORY_MANAGER` only
- `require_any_staff` → both roles

---

## API Endpoints

```
POST  /api/v1/auth/signup
POST  /api/v1/auth/login
POST  /api/v1/auth/otp/send
POST  /api/v1/auth/otp/verify-and-reset
GET   /api/v1/auth/me

GET   /api/v1/products/
POST  /api/v1/products/
PUT   /api/v1/products/{id}

POST  /api/v1/operations/
POST  /api/v1/operations/{id}/lines
POST  /api/v1/operations/{id}/validate

GET   /api/v1/dashboard/kpis
GET   /api/v1/dashboard/filter

GET   /api/v1/ledger/moves

GET   /health
```

---

## Seeded Data (auto-created on first startup)

| Entity | Value |
|--------|-------|
| Warehouse | Main Warehouse (WH01) |
| Location | WH01/Stock (INTERNAL) |
| Location | Virtual/Vendor (VENDOR) |
| Location | Virtual/Customer (CUSTOMER) |
| Location | Virtual/Inventory-Loss (INVENTORY_LOSS) |
| Category | General |
| Admin user | admin@stocksense.local / Admin@123 |

> [!IMPORTANT]
> Change `ADMIN_PASSWORD` and `SECRET_KEY` in `.env` before any production deployment.
