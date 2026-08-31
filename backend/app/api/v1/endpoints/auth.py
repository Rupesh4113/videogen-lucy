"""
Authentication REST API Endpoints for Videogen-Lucy.
Supports Dual-Mode Login:
1. Email & Password Registration and Login
2. Mobile Number & 6-Digit OTP Login / Auto-Provisioning (via Open-Source Mobile Notification or SMS Gateway)
"""
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from backend.app.models.database import get_db
from backend.app.models.entities import User, OTPToken
from backend.app.schemas.auth import (
    RegisterRequest, LoginRequest, SendOTPRequest, SendOTPResponse,
    VerifyOTPRequest, TokenResponse, UserResponse
)
from backend.app.utils.security import (
    hash_password, verify_password, create_access_token, generate_otp_code
)
from backend.app.providers.sms.factory import SMSProviderFactory
from backend.app.api.deps import get_current_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account with Email, Password, Name, and optional Phone.
    """
    email_clean = payload.email.lower().strip()
    
    # Check if email already exists
    stmt = select(User).where(User.email == email_clean)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # If phone is provided, check if phone already exists
    if payload.phone_number:
        phone_clean = payload.phone_number.strip()
        p_stmt = select(User).where(User.phone_number == phone_clean)
        if (await db.execute(p_stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this phone number already exists."
            )
    else:
        phone_clean = None

    # Create new user
    new_user = User(
        email=email_clean,
        name=payload.name or email_clean.split("@")[0].capitalize(),
        phone_number=phone_clean,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_verified=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate JWT
    token = create_access_token({"sub": new_user.id, "email": new_user.email, "name": new_user.name})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with Email and Password.
    """
    email_clean = payload.email.lower().strip()
    stmt = select(User).where(User.email == email_clean)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/otp/send", response_model=SendOTPResponse)
async def send_otp_code(
    payload: SendOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and deliver a 6-digit OTP code to a mobile phone number or email.
    Uses Open-Source Mobile Notification Gateway (ntfy.sh / Android Gateway / Cellular).
    """
    identifier = payload.phone_or_email.strip()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number or email is required."
        )

    # Generate 6-digit OTP and set 10-minute expiry
    otp_code = generate_otp_code(6)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    otp_record = OTPToken(
        phone_or_email=identifier,
        otp_code=otp_code,
        purpose="login",
        expires_at=expires_at,
        is_used=False
    )
    db.add(otp_record)
    await db.commit()

    # Deliver via SMS provider (defaults to open-source mobile push / Android gateway)
    sms_provider = SMSProviderFactory.get_sms_provider()
    delivery_res = await sms_provider.send_otp(identifier, otp_code)

    return SendOTPResponse(
        success=True,
        message=delivery_res.get("message", f"OTP code successfully sent to {identifier}."),
        phone_or_email=identifier,
        provider=delivery_res.get("provider", "opensource"),
        mobile_url=delivery_res.get("mobile_url"),
        dev_otp_code=otp_code
    )


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp_code(
    payload: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify 6-digit OTP code. Auto-provisions new user if phone does not exist yet.
    """
    identifier = payload.phone_or_email.strip()
    otp_input = payload.otp_code.strip()
    now_utc = datetime.now(timezone.utc)

    # Find valid, unexpired, unused OTP record
    stmt = select(OTPToken).where(
        OTPToken.phone_or_email == identifier,
        OTPToken.otp_code == otp_input,
        OTPToken.is_used == False,
        OTPToken.expires_at > now_utc
    ).order_by(OTPToken.created_at.desc())

    record = (await db.execute(stmt)).scalars().first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP verification code."
        )

    # Mark OTP as used
    record.is_used = True
    await db.commit()

    # Find or auto-create User account
    user_stmt = select(User).where(
        or_(User.phone_number == identifier, User.email == identifier)
    )
    user = (await db.execute(user_stmt)).scalar_one_or_none()

    if not user:
        is_email = "@" in identifier
        user = User(
            email=identifier if is_email else None,
            phone_number=None if is_email else identifier,
            name=payload.name or (identifier.split("@")[0].capitalize() if is_email else f"User {identifier[-4:]}"),
            is_active=True,
            is_verified=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token({
        "sub": user.id,
        "email": user.email or user.phone_number,
        "name": user.name
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve authenticated user profile and account details.
    """
    return UserResponse.model_validate(current_user)
