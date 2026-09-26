# 📦 StockSense

An advanced, double-entry inventory management system built with FastAPI, PostgreSQL, and modern web technologies. Inspired by industry-standard systems like Odoo, StockSense ensures precise tracking of every product movement across warehouses, vendors, and customers with strict ACID compliance.

---

## 🌟 Key Features

- **Double-Entry Ledger System:** Every stock movement is tracked as a transfer between two locations (e.g., Vendor → Warehouse). Nothing is created or destroyed out of thin air.
- **ACID Compliant Transactions:** Concurrency control prevents race conditions during stock validation, ensuring inventory counts are always mathematically perfectly balanced.
- **Role-Based Access Control (RBAC):** Distinct permissions for `INVENTORY_MANAGER` and `STAFF`.
- **PostgreSQL-Native OTP:** Password reset workflows handled entirely within PostgreSQL (no Redis required), featuring built-in brute-force protection and cooldowns.
- **Dynamic KPI Dashboard:** Real-time metrics and dynamic filtering for actionable business insights.

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.10+)
- **Database:** PostgreSQL (Asyncpg)
- **ORM:** SQLAlchemy 2.0 (Async)
- **Data Validation:** Pydantic v2
- **Authentication:** JWT (JSON Web Tokens) & bcrypt

### Frontend
- **Framework:** Next.js / React (TypeScript)
- **Styling:** Tailwind CSS
- **State Management:** React Context / Hooks

---

## 🚀 Step-by-Step Execution Guide

### 1. Prerequisites
Before starting, ensure you have the following installed on your machine:
- **Python 3.10+**
- **Node.js 18+** (for the frontend)
- **PostgreSQL** running locally

### 2. Backend Setup
Navigate to the root directory (where `main.py` is located) and follow these steps:

**Step A: Configure Environment Variables**
Copy the template file and fill in your details:
```powershell
Copy-Item .env.example .env
```
Ensure you update the `DATABASE_URL` to match your local PostgreSQL credentials and set a secure `SECRET_KEY`.

**Step B: Prepare the Database**
Create the database in PostgreSQL:
```powershell
psql -U postgres -c "CREATE DATABASE stocksense_db;"
```

**Step C: Install Dependencies**
Create a virtual environment (optional but recommended) and install packages:
```powershell
pip install -r requirements.txt
```

**Step D: Run the Server**
Launch the FastAPI backend. *Note: Tables and default seed data are automatically generated on the first startup!*
```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Visit **http://127.0.0.1:8000/docs** to interact with the API via Swagger UI.

### 3. Frontend Setup (Next.js)
Open a new terminal window, navigate to the `frontend/` directory, and run the development server:
```powershell
cd frontend
npm install
npm run dev
```
Visit **http://localhost:3000** to access the application UI.

---

## 🧠 Architecture Decisions

### The Double-Entry Engine
Every stock operation moves quantity **between** two distinct locations. This design guarantees an unbroken audit trail:

| Operation Type | Source Location | Destination Location |
|----------------|-----------------|----------------------|
| **Receipt** | `Virtual/Vendor` | `WH01/Stock` |
| **Delivery** | `WH01/Stock` | `Virtual/Customer` |
| **Transfer** | `Internal A` | `Internal B` |
| **Inventory Gain**| `Virtual/Inventory-Loss`| `Internal` |
| **Inventory Loss**| `Internal` | `Virtual/Inventory-Loss`|

### Handling Concurrency (ACID)
When a stock operation is validated (e.g., shipping items out), the system must guarantee the stock isn't simultaneously allocated to another order.
- The `validate` endpoint uses nested transactions `db.begin_nested()` (savepoints).
- Rows in `StockQuant` are locked via `.with_for_update()` before reading.
- If an `InsufficientStockException` is raised, the savepoint automatically rolls back.

---

## 📂 Backend Project Structure

| File | Purpose |
|------|---------|
| `main.py` | FastAPI application entrypoint and lifespan events. |
| `app/config.py` | Pydantic-settings singleton for strict environment validation. |
| `app/database.py` | Async database engine, session maker, and dependencies. |
| `app/models.py` | SQLAlchemy ORM models representing the schema. |
| `app/schemas.py` | Pydantic v2 schemas for request and response validation. |
| `app/security.py` | Utilities for password hashing, JWT signing, and RBAC dependencies. |
| `app/seed.py` | Idempotent script that populates the DB with default data on startup. |
| `app/services/inventory.py`| **The Core Engine** - validates and executes double-entry logic. |
| `app/routers/*.py`| API endpoints separated by domain (auth, products, operations, etc). |

---

## 🔐 Default Seeded Data

On the first successful startup, the system automatically creates foundational records:

**Default Administrator Account:**
- **Email:** `admin@stocksense.local`
- **Password:** `Admin@123`

**Default Locations Created:**
- Main Warehouse (`WH01`)
- Internal Stock (`WH01/Stock`)
- Vendor (`Virtual/Vendor`)
- Customer (`Virtual/Customer`)
- Inventory Loss (`Virtual/Inventory-Loss`)

> **⚠️ Security Warning:** Change the `ADMIN_PASSWORD` and `SECRET_KEY` in your `.env` file before deploying to a production environment.

---

## 📡 Core API Endpoints

**Authentication**
- `POST /api/v1/auth/signup` - Register a new staff member.
- `POST /api/v1/auth/login` - Authenticate and receive JWT.
- `POST /api/v1/auth/otp/send` - Send password reset OTP.

**Products & Inventory**
- `GET /api/v1/products/` - Retrieve paginated list of products.
- `POST /api/v1/products/` - Create a new product template.
- `GET /api/v1/ledger/moves` - View the immutable double-entry ledger.

**Operations**
- `POST /api/v1/operations/` - Create a draft shipment or receipt.
- `POST /api/v1/operations/{id}/lines` - Add products to the draft.
- `POST /api/v1/operations/{id}/validate` - Execute and confirm the movement.
