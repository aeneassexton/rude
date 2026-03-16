"""JWT authentication middleware for BFE API.

Validates Supabase-issued JWTs on every protected route.
The SUPABASE_JWT_SECRET environment variable must be set on Railway.

Usage:
    from auth import get_current_user

    @app.get("/forecast/{user_id}")
    def get_forecast(user_id: str, current_user: dict = Depends(get_current_user)):
        # current_user["sub"] is the authenticated Supabase user UUID
        if current_user["sub"] != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        ...
"""
import os
import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

_JWT_SECRET  = os.getenv("SUPABASE_JWT_SECRET", "")
_JWT_ALGO    = "HS256"
_bearer      = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """Validate Bearer token and return decoded payload.

    Raises 401 if token is missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _JWT_SECRET:
        logger.error("auth SUPABASE_JWT_SECRET not set — all requests will be rejected")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            _JWT_SECRET,
            algorithms=[_JWT_ALGO],
            options={"verify_aud": False},  # Supabase tokens use "authenticated" audience
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("auth invalid_token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_self(user_id: str, current_user: dict) -> None:
    """Raise 403 if the authenticated user doesn't match the requested user_id."""
    if current_user.get("sub") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own data",
        )
