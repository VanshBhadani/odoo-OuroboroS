"""
main.py
───────
StockSense FastAPI application entry point.

Responsibilities:
  - Define application lifespan (startup seeding, graceful engine disposal).
  - Register all API routers under /api/v1.
  - Configure global exception handlers.
  - Expose the ASGI app for uvicorn.

Run locally:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import engine
from app.routers import auth, dashboard, ledger, operations, products, settings
from app.seed import run_seed

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stocksense")


# ─────────────────────────────────────────────────────────────────────────────
# Application lifespan
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.

    startup  → create tables + seed reference data.
    shutdown → dispose async SQLAlchemy engine pool gracefully.

    NOTE: seed errors are non-fatal so the app (and Swagger UI) can still start
    even when the database is temporarily unreachable.  The error is logged at
    WARNING level and the application continues to run.
    """
    logger.info("StockSense starting up …")
    try:
        await run_seed()
        logger.info("StockSense is ready to serve requests.")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Startup seed failed (DB may be unreachable): %s – "
            "the application will still start but database-backed endpoints may fail.",
            exc,
        )

    yield  # application runs here

    logger.info("StockSense shutting down …")
    await engine.dispose()
    logger.info("Database engine disposed. Bye!")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="StockSense – Inventory Management System",
    description=(
        "A production-ready, ledger-based inventory management backend built with "
        "FastAPI, SQLAlchemy 2.0 (async), and native PostgreSQL.\n\n"
        "**Architecture highlights:**\n"
        "- Double-entry stock movements (append-only ledger)\n"
        "- ACID-compliant transactions with `SELECT … FOR UPDATE` concurrency control\n"
        "- JWT authentication with RBAC (INVENTORY_MANAGER / WAREHOUSE_STAFF)\n"
        "- PostgreSQL-native OTP verification (no Redis)\n"
    ),
    version="1.0.0",
    contact={
        "name": "StockSense Engineering",
        "email": "admin@stocksense.dev",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Global exception handlers
# ─────────────────────────────────────────────────────────────────────────────
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler: log the full traceback and return a 500 response.

    IMPORTANT: StarletteHTTPException and RequestValidationError are re-raised so that
    FastAPI's own built-in handlers process them correctly.  Without this, those
    exception types would be swallowed here and could corrupt schema generation
    or hide validation errors behind a generic 500.
    """
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        raise exc
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal error occurred. Please try again."},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Router registration
# ─────────────────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(operations.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(ledger.router, prefix=API_PREFIX)
app.include_router(settings.router, prefix=API_PREFIX)


# ─────────────────────────────────────────────────────────────────────────────
# Health check (no auth required)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Health check")
async def health_check() -> dict:
    """Returns 200 OK if the service is running."""
    return {"status": "ok", "service": "StockSense", "version": "1.0.0"}


@app.get("/", tags=["System"], include_in_schema=False)
async def root() -> dict:
    """Redirect hint for API consumers."""
    return {
        "message": "Welcome to StockSense API",
        "docs": "/docs",
        "health": "/health",
    }
