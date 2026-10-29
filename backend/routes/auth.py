"""
DSFMP Fraud Detection — Authentication Router

Implements:
- POST /api/auth/login
- POST /api/auth/verify-2fa
- POST /api/auth/refresh
- POST /api/auth/logout
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    create_temp_token,
    verify_totp,
    decode_token,
)
from database.connection import get_db
from database.redis import get_redis, RedisKeys
from models.user import User
from schemas.auth import (
    LoginRequest,
    LoginResponse,
    Verify2FARequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from middleware.dependencies import oauth2_scheme, get_current_user

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
    description="Initiates login. If 2FA is enabled, returns a temp_token. Otherwise returns access + refresh tokens.",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Handle 2FA
    if user.two_fa_enabled:
        if not user.two_fa_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="2FA is enabled but no TOTP secret is configured",
            )
        temp_token = create_temp_token(
            {"sub": user.id, "email": user.email, "role": user.role}
        )
        return LoginResponse(requires_2fa=True, temp_token=temp_token)

    # Issue full tokens if 2FA is not enabled
    jti = str(uuid.uuid4())
    access_token = create_access_token(
        {"sub": user.id, "email": user.email, "role": user.role, "jti": jti}
    )
    refresh_token = create_refresh_token(
        {"sub": user.id, "email": user.email, "role": user.role}
    )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return LoginResponse(
        requires_2fa=False,
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/verify-2fa",
    response_model=LoginResponse,
    summary="Verify 2FA TOTP code",
    description="Verifies the TOTP code using a temp_token and returns access + refresh tokens.",
)
async def verify_2fa(
    request: Verify2FARequest,
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired temporary token",
    )

    # Decode and validate the temporary 2FA token
    try:
        payload = decode_token(request.temp_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "temp_2fa":
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # Load user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    # Verify code
    if not user.two_fa_secret or not verify_totp(user.two_fa_secret, request.otp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code",
        )

    # Issue tokens
    jti = str(uuid.uuid4())
    access_token = create_access_token(
        {"sub": user.id, "email": user.email, "role": user.role, "jti": jti}
    )
    refresh_token = create_refresh_token(
        {"sub": user.id, "email": user.email, "role": user.role}
    )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return LoginResponse(
        requires_2fa=False,
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Validates a refresh token and returns a new access + refresh token pair.",
)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    refresh_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        payload = decode_token(request.refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "refresh":
            raise refresh_exception
    except Exception:
        raise refresh_exception

    # Load user to ensure active status
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise refresh_exception

    # Issue new token pair
    jti = str(uuid.uuid4())
    new_access_token = create_access_token(
        {"sub": user.id, "email": user.email, "role": user.role, "jti": jti}
    )
    new_refresh_token = create_refresh_token(
        {"sub": user.id, "email": user.email, "role": user.role}
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post(
    "/logout",
    summary="Log out of the system",
    description="Blacklists the current access token in Redis to prevent reuse.",
)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    current_user: Annotated[User, Depends(get_current_user)],
    redis = Depends(get_redis),
):
    if redis is not None:
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                now = datetime.now(timezone.utc).timestamp()
                ttl = int(exp - now)
                if ttl > 0:
                    await redis.setex(RedisKeys.blacklisted_token(jti), ttl, "true")
        except Exception:
            # Fail silently to allow logout even if token parsing has issues
            pass

    return {"message": "Successfully logged out"}
