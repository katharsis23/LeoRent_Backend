from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.leorent_backend.models import Apartment
from src.leorent_backend.models import Liked, UserType
from src.leorent_backend.database_connector import AsyncSession
from loguru import logger
from uuid import UUID
from fastapi import HTTPException
import src.leorent_backend.schemas.apartment as apartment_schemas
import src.leorent_backend.database.user as user_db
from typing import Optional, List


async def get_apartments(db: AsyncSession, current_page: int = 1, page_size: int = 10):
    try:
        result = await db.execute(
            select(Apartment)
            .where(Apartment.is_deleted == False)   # noqa: E712
            .offset((current_page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting apartments: {e}")
        raise e


async def create_apartment(
    db: AsyncSession,
    apartment: apartment_schemas.ApartmentCreate,
    user_id: UUID,
):
    try:
        db_apartment = Apartment(**apartment.model_dump(), owner=user_id)
        db.add(db_apartment)
        await db.commit()
        await db.refresh(db_apartment)
        return db_apartment
    except Exception as e:
        logger.error(f"Error creating apartment: {e}")
        raise e


async def get_apartment(db: AsyncSession, apartment_id: UUID):
    try:
        result = await db.execute(
            select(Apartment)
            .options(selectinload(Apartment.owner_user))
            .where(Apartment.id_ == apartment_id)
            .where(Apartment.is_deleted == False)   # noqa: E712
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting apartment: {e}")
        raise e


async def is_allowed_to_create_apartment(db: AsyncSession, user_id: UUID) -> bool:
    try:
        user_ = await user_db.find_user_by_id(user_id, db)
        if user_:
            return user_.type_ in (UserType.AGENT, UserType.OWNER)
        return False
    except Exception as e:
        logger.error(f"Error checking if user is allowed to create apartment: {e}")
        raise e


async def get_user_type_from_apartment(
    db: AsyncSession,
    apartment_id: UUID
) -> Optional[UserType]:
    try:
        apartment = await get_apartment(db, apartment_id)
        if apartment and apartment.owner_user:
            return apartment.owner_user.type_
        return None
    except Exception as e:
        logger.error(f"Error getting user type from apartment: {e}")
        raise e


async def is_apartment_liked_by_user(
    db: AsyncSession,
    apartment_id: UUID,
    user_id: UUID
) -> bool:
    try:
        result = await db.execute(
            select(Liked).where(
                Liked.apartment_id == apartment_id,
                Liked.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.error(f"Error checking if apartment is liked by user: {e}")
        raise e


async def update_apartment(
    db: AsyncSession,
    apartment_id: UUID,
    apartment_update: apartment_schemas.ApartmentUpdate,
    user_id: UUID
) -> Optional[Apartment]:
    try:
        apartment = await get_apartment(db, apartment_id)
        if not apartment:
            return None

        if apartment.owner != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to update this apartment"
            )

        update_data = apartment_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(apartment, field, value)

        await db.commit()
        await db.refresh(apartment)
        return apartment
    except Exception as e:
        logger.error(f"Error updating apartment: {e}")
        raise e


async def delete_apartment(
    db: AsyncSession,
    apartment_id: UUID,
    user_id: UUID
) -> bool:
    try:
        # Find apartment without filtering by is_deleted
        result = await db.execute(
            select(Apartment)
            .where(Apartment.id_ == apartment_id)
        )
        apartment = result.scalar_one_or_none()

        if not apartment:
            return False

        if apartment.is_deleted:
            # Already deleted, return False to indicate nothing was deleted
            return False

        if apartment.owner != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to delete this apartment"
            )

        apartment.is_deleted = True
        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error deleting apartment: {e}")
        raise e


async def get_apartments_by_user(
    db: AsyncSession,
    user_id: UUID,
    current_page: int = 1,
    page_size: int = 10
) -> List[Apartment]:
    try:
        query = select(Apartment).where(Apartment.owner == user_id)
        result = await db.execute(
            query
            .offset((current_page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting apartments by user: {e}")
        raise e


async def get_liked_apartments_by_user(
    db: AsyncSession,
    user_id: UUID
) -> List[Apartment]:
    try:
        query = select(Liked.apartment_id).where(Liked.user_id == user_id)
        result = await db.execute(query)
        apartment_ids = result.scalars().all()

        if not apartment_ids:
            return []

        query = select(Apartment).where(Apartment.id_.in_(apartment_ids))
        result = await db.execute(query)
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting liked apartments by user: {e}")
        raise e


async def toggle_like_apartment(
    db: AsyncSession,
    apartment_id: UUID,
    user_id: UUID
) -> dict:
    """
    Toggle like status for an apartment.
    Returns dict with action taken and apartment_id.
    """
    try:
        # Check if apartment exists and is not deleted
        apartment_result = await db.execute(
            select(Apartment)
            .where(Apartment.id_ == apartment_id)
            .where(Apartment.is_deleted == False)   # noqa: E712
        )
        apartment = apartment_result.scalar_one_or_none()

        if not apartment:
            return {"error": "Apartment not found or deleted"}

        # Check if already liked
        result = await db.execute(
            select(Liked)
            .where(Liked.apartment_id == apartment_id)
            .where(Liked.user_id == user_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Unlike - remove the like
            await db.delete(existing)
            await db.commit()
            return {
                "action": "unliked",
                "apartment_id": str(apartment_id),
                "message": "Apartment unliked successfully"
            }
        else:
            # Like - add new like
            like = Liked(apartment_id=apartment_id, user_id=user_id)
            db.add(like)
            await db.commit()
            return {
                "action": "liked",
                "apartment_id": str(apartment_id),
                "message": "Apartment liked successfully"
            }
    except Exception as e:
        logger.error(f"Error toggling like for apartment: {e}")
        raise e


async def like_apartment(
    db: AsyncSession,
    apartment_id: UUID,
    user_id: UUID
) -> Optional[Apartment]:
    try:
        # Check if already liked
        result = await db.execute(
            select(Liked)
            .where(Liked.apartment_id == apartment_id)
            .where(Liked.user_id == user_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return None  # Already liked

        # Create new like
        like = Liked(apartment_id=apartment_id, user_id=user_id)
        db.add(like)
        await db.commit()
        return like.apartment_id
    except Exception as e:
        logger.error(f"Error liking apartment: {e}")
        raise e


async def get_apartments_by_gemini_filter(
    db: AsyncSession,
    filter_query: dict,
    current_page: int = 1,
    page_size: int = 10
) -> Optional[List[Apartment]]:
    try:
        # TODO: Add class For validationkf
        # Consider using schemas but aware of circular import issue
        pass
        return None
    except Exception as e:
        logger.error(f"Error getting apartments by Gemini filter: {e}")
        raise e
