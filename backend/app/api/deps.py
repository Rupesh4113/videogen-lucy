"""
Authentication and Database Dependencies for FastAPI endpoints.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.database import get_db
from backend.app.models.entities import User
from backend.app.utils.security import decode_access_token


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Extracts and validates the current user from the Authorization: Bearer <token> header.
    Returns None if no token or invalid token is supplied (allowing guest access).
    """
    if not authorization:
        return None

    token = authorization
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    user_id = payload["sub"]
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user and user.is_active:
        return user

    return None


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """
    Strict dependency: Requires a valid authenticated user, else raises 401 Unauthorized.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
