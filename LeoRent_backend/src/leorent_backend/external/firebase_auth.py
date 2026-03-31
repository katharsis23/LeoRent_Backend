from src.leorent_backend.database.user import (
    create_user_from_firebase, find_user_by_firebase_uid
)
from src.leorent_backend.external import firebase_client
from firebase_admin import auth
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.leorent_backend.database_connector import get_db
from src.leorent_backend.models import Users, UserType
from loguru import logger
from typing import Optional

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    user_type: Optional[UserType] = None
) -> Users:  # noqa: C901
    """
    Get current authenticated user from Firebase token

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        Users: Current authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not firebase_client.firebase_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase service not available",
        )

    try:
        # Verify Firebase ID token
        decoded_token = auth.verify_id_token(
            credentials.credentials,
            check_revoked=True,
            clock_skew_seconds=10
        )
        firebase_uid = decoded_token.get('uid')

        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing UID",
            )

        # Find user in database
        user = await find_user_by_firebase_uid(firebase_uid, db)
        if not user:
            # Extract user info from Firebase token if not provided
            if not first_name:
                first_name = decoded_token.get('first_name') or decoded_token.get('name', '').split(' ')[0] or ''
            if not last_name:
                last_name = decoded_token.get('last_name') or (decoded_token.get('name', '').split(' ')[1] if ' ' in decoded_token.get('name', '') else '') or ''

            # For phone and user_type, they MUST be provided if we create a user
            if not phone:
                phone = decoded_token.get('phone_number') or ''

            if not user_type:
                user_type = UserType.DEFAULT

            user = await create_user_from_firebase(
                decoded_token, first_name, last_name, phone, user_type, db
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found and creation failed",
            )

        return user

    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
