"""
app/routers/auth.py
───────────────────
Authentication endpoints:
  POST /signup
  POST /login
  POST /otp/send
  POST /otp/verify-and-reset
"""

from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import OtpVerification, User
from app.schemas import (
    LoginRequest,
    MessageResponse,
    OtpSendRequest,
    OtpVerifyRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
)
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /signup
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> User:
    """Create a new user.  Email must be unique."""
    # Check duplicate email
    existing = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered.",
        )

    user = User(
        email=payload.email.lower(),
        name=payload.name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    logger.info("New user registered: %s (%s)", user.email, user.role)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# POST /login
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain a Bearer JWT",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Verify credentials and return a signed JWT access token."""
    result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token(subject=str(user.id), role=user.role.value)
    logger.info("User logged in: %s", user.email)
    return {"access_token": token, "token_type": "bearer"}


# ─────────────────────────────────────────────────────────────────────────────
# POST /otp/send
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/otp/send",
    response_model=MessageResponse,
    summary="Generate and send (log) a 6-digit OTP for password reset",
)
async def send_otp(payload: OtpSendRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Rate-limit: reject if a valid (unexpired) OTP was issued within the last
    60 seconds for this email.

    The OTP is bcrypt-hashed before storage.  The plain-text code is emitted
    to server logs to simulate email dispatch (no external SMTP required).
    """
    email = payload.email.lower()

    # ── Verify user exists ────────────────────────────────────────────────────
    user_result = await db.execute(select(User).where(User.email == email))
    user: User | None = user_result.scalar_one_or_none()
    if user is None:
        # Return generic message to avoid user enumeration
        logger.warning("OTP requested for non-existent email: %s", email)
        return {"message": "If this email is registered, an OTP has been sent."}

    # ── Cooldown check ────────────────────────────────────────────────────────
    cooldown_cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.OTP_RESEND_COOLDOWN_SECONDS
    )
    recent_result = await db.execute(
        select(OtpVerification).where(
            and_(
                OtpVerification.email == email,
                OtpVerification.is_used.is_(False),
                OtpVerification.expires_at > datetime.now(timezone.utc),
                OtpVerification.created_at > cooldown_cutoff,
            )
        )
    )
    if recent_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Please wait {settings.OTP_RESEND_COOLDOWN_SECONDS} seconds "
                "before requesting a new OTP."
            ),
        )

    # ── Generate OTP ──────────────────────────────────────────────────────────
    otp_plain = "".join(random.choices(string.digits, k=6))
    otp_hash = hash_password(otp_plain)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.OTP_EXPIRE_MINUTES
    )

    otp_record = OtpVerification(
        email=email,
        otp_hash=otp_hash,
        expires_at=expires_at,
        user_id=str(user.id),
    )
    db.add(otp_record)
    await db.flush()

    # ── Secure log (simulates email dispatch) ─────────────────────────────────
    logger.info(
        "OTP for %s: %s  (expires %s UTC)  [SIMULATED EMAIL]",
        email,
        otp_plain,
        expires_at.isoformat(),
    )

    return {"message": "If this email is registered, an OTP has been sent."}


# ─────────────────────────────────────────────────────────────────────────────
# POST /otp/verify-and-reset
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/otp/verify-and-reset",
    response_model=MessageResponse,
    summary="Verify OTP and reset user password",
)
async def verify_otp_and_reset(
    payload: OtpVerifyRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Validates the OTP and resets the user's password atomically.

    Rules enforced:
    * OTP must be unexpired (expires_at > NOW()).
    * OTP must not be already used (is_used = FALSE).
    * Max 3 failed attempts before the OTP is permanently locked.
    """
    email = payload.email.lower()
    now = datetime.now(timezone.utc)

    # ── Look up the most recent valid OTP ─────────────────────────────────────
    otp_result = await db.execute(
        select(OtpVerification)
        .where(
            and_(
                OtpVerification.email == email,
                OtpVerification.is_used.is_(False),
                OtpVerification.expires_at > now,
            )
        )
        .order_by(OtpVerification.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    otp_record: OtpVerification | None = otp_result.scalar_one_or_none()

    if otp_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid OTP found for this email. Request a new code.",
        )

    # ── Brute-force guard ─────────────────────────────────────────────────────
    if otp_record.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="OTP is locked after too many failed attempts. Request a new code.",
        )

    # ── Verify OTP ────────────────────────────────────────────────────────────
    if not verify_password(payload.otp, otp_record.otp_hash):
        otp_record.attempts += 1
        await db.flush()
        remaining = settings.OTP_MAX_ATTEMPTS - otp_record.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
        )

    # ── Mark OTP as used ──────────────────────────────────────────────────────
    otp_record.is_used = True

    # ── Update user password ──────────────────────────────────────────────────
    user_result = await db.execute(select(User).where(User.email == email))
    user: User | None = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    user.hashed_password = hash_password(payload.new_password)
    user.updated_at = now
    await db.flush()

    logger.info("Password reset successful for: %s", email)
    return {"message": "Password has been reset successfully."}


# ─────────────────────────────────────────────────────────────────────────────
# GET /me  (bonus – returns current user profile)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserOut,
    summary="Return the profile of the currently authenticated user",
)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Protected endpoint – requires valid Bearer token."""
    return current_user
