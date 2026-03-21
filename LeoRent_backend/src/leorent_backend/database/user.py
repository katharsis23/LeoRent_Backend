from src.leorent_backend.models import Users
from src.leorent_backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID as PythonUUID
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger


async def find_user_by_id(user_id: PythonUUID, db: AsyncSession) -> Optional[Users]:
    """
    Main function to find user by his UUID

    Returns User object if found, else None
    """
    try:
        query = await db.execute(select(Users).where(Users.id_ == user_id))
        user = query.scalar_one_or_none()
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error finding user by ID: {e}")
        return None


async def find_user_by_firebase_uid(
    firebase_uid: str, db: AsyncSession
) -> Optional[Users]:
    """
    Find user by Firebase UID

    Args:
        firebase_uid: Firebase user UID
        db: Database session

    Returns:
        Users: User object if found, else None
    """
    try:
        query = await db.execute(
            select(Users).where(Users.firebase_uid == firebase_uid)
        )
        user = query.scalar_one_or_none()
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error finding user by Firebase UID: {e}")
        return None


async def create_user() -> Optional[Users]:
    pass
