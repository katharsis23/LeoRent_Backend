from src.leorent_backend.external.firebase_client import firebase_app
from firebase_admin import auth
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.leorent_backend.database import get_db
from src.leorent_backend.database.user import find_user_by_firebase_uid
from src.leorent_backend.models import Users
from loguru import logger
from typing import Optional

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Users:
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

    if not firebase_app:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase service not available",
        )

    try:
        # Verify Firebase ID token
        decoded_token = auth.verify_id_token(credentials.credentials)
        firebase_uid = decoded_token.get('uid')

        if not firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing UID",
            )

        # Find user in database
        user = await find_user_by_firebase_uid(firebase_uid, db)

        # if not user:
        #     # Create new user if doesn't exist
        #     user = await create_user_from_firebase(decoded_token, db)

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
