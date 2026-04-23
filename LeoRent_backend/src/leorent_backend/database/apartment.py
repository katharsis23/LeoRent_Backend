from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.leorent_backend.models import Apartment, Liked, Pictures, UserType
from src.leorent_backend.database_connector import AsyncSession
from loguru import logger
from uuid import UUID
from sqlalchemy import update
from fastapi import HTTPException
import src.leorent_backend.schemas.apartment as apartment_schemas
import src.leorent_backend.database.user as user_db
from typing import Optional, List
from src.leorent_backend.schemas.filter import FilterApartment
from sqlalchemy import func
from datetime import datetime


async def get_apartments(
    db: AsyncSession,
    current_page: int = 1,
    page_size: int = 6,
    filters: dict | None = None,
    sort: str = "newest",
) -> tuple[list, int]:
    try:
        # Validate sort parameter
        valid_sorts = ["newest", "oldest", "price_asc", "price_desc"]
        if sort not in valid_sorts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort parameter. Must be one of: {valid_sorts}"
            )
        filters = filters or {}
        conditions = [Apartment.is_deleted == False]  # noqa

        if filters.get("district"):
            conditions.append(Apartment.district == filters["district"])
        if filters.get("price_min"):
            conditions.append(Apartment.cost >= filters["price_min"])
        if filters.get("price_max"):
            conditions.append(Apartment.cost <= filters["price_max"])
        if filters.get("rooms"):
            conditions.append(Apartment.rooms.in_(filters["rooms"]))
        if filters.get("square_min"):
            conditions.append(Apartment.square >= filters["square_min"])
        if filters.get("square_max"):
            conditions.append(Apartment.square <= filters["square_max"])
        if filters.get("floor_min"):
            conditions.append(Apartment.floor >= filters["floor_min"])
        if filters.get("floor_max"):
            conditions.append(Apartment.floor <= filters["floor_max"])
        if filters.get("rent_type") and filters["rent_type"] != "all":
            conditions.append(Apartment.rent_type == filters["rent_type"])
        if filters.get("owner_type") and filters["owner_type"] != "all":
            from src.leorent_backend.models import Users
            conditions.append(
                Apartment.owner.in_(
                    select(Users.id_).where(Users.type_ == filters["owner_type"])
                )
            )

        # sort
        from sqlalchemy import asc, desc
        order = desc(Apartment.created_at)  # Default: newest first
        if sort == "price_asc":
            order = asc(Apartment.cost)
        elif sort == "price_desc":
            order = desc(Apartment.cost)
        elif sort == "oldest":
            order = asc(Apartment.created_at)
        elif sort == "newest":
            order = desc(Apartment.created_at)

        # total count
        count_q = select(func.count()).select_from(Apartment).where(*conditions)
        total = (await db.execute(count_q)).scalar() or 0

        # paginated
        q = (
            select(Apartment)
            .options(selectinload(Apartment.pictures))
            .where(*conditions)
            .order_by(order)
            .offset((current_page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(q)
        return result.scalars().all(), total

    except Exception as e:
        logger.error(f"Error getting apartments: {e}")
        raise e


async def create_apartment(
    db: AsyncSession,
    apartment: apartment_schemas.ApartmentCreate,
    user_id: UUID,
    pictures: Optional[List[dict]] = None,
):
    try:
        apartment_data = apartment.model_dump(exclude={"main_pictures"})
        picture_records = pictures or []
        db_apartment = Apartment(
            **apartment_data,
            owner=user_id,
            main_picture=(
                picture_records[0]["url"] if picture_records else None),
        )
        db.add(db_apartment)
        await db.flush()
        created_apartment_id = db_apartment.id_

        for picture in picture_records:
            metadata = {
                key: value
                for key, value in dict(picture.get("metadata") or {}).items()
                if key != "is_main"
            }
            db.add(
                Pictures(
                    apartment_id=db_apartment.id_,
                    url=picture["url"],
                    metadata_=metadata,
                )
            )

        await db.commit()
        db.expire_all()

        result = await db.execute(
            select(Apartment)
            .options(selectinload(Apartment.pictures))
            .where(Apartment.id_ == created_apartment_id)
        )
        return result.scalar_one()
    except Exception as e:
        logger.error(f"Error creating apartment: {e}")
        raise e


async def get_apartment(db: AsyncSession, apartment_id: UUID):
    try:
        result = await db.execute(
            select(Apartment)
            .options(
                selectinload(Apartment.owner_user),
                selectinload(Apartment.pictures),
            )
            .where(Apartment.id_ == apartment_id)
            .where(Apartment.is_deleted == False)   # noqa: E712
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting apartment: {e}")
        raise e


async def add_apartment_pictures(
    db: AsyncSession,
    apartment_id: UUID,
    pictures: List[dict],
) -> Optional[Apartment]:
    try:
        apartment = await get_apartment(db, apartment_id)
        if not apartment:
            return None

        for picture in pictures:
            metadata = picture.get("metadata") or {}
            db.add(
                Pictures(
                    apartment_id=apartment_id,
                    url=picture["url"],
                    metadata_=metadata,
                )
            )

        await db.commit()
        db.expire_all()
        return await get_apartment(db, apartment_id)
    except Exception as e:
        logger.error(f"Error adding apartment pictures: {e}")
        raise e


async def soft_delete_all_apartment_pictures(
    db: AsyncSession,
    apartment_id: UUID,
    user_id: UUID,
) -> bool:
    try:
        apartment = await get_apartment(db, apartment_id)
        if not apartment:
            return False

        if apartment.owner != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to delete apartment pictures",
            )

        conditions = [
            Pictures.apartment_id == apartment_id,
            Pictures.is_deleted.is_(False),
        ]
        if apartment.main_picture:
            conditions.append(Pictures.url != apartment.main_picture)

        await db.execute(
            update(Pictures)
            .where(*conditions)
            .values(is_deleted=True)
        )

        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error soft deleting all apartment pictures: {e}")
        raise e


async def soft_delete_apartment_picture(
    db: AsyncSession,
    apartment_id: UUID,
    picture_id: UUID,
    user_id: UUID,
) -> bool:
    try:
        apartment = await get_apartment(db, apartment_id)
        if not apartment:
            return False

        if apartment.owner != user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to delete this picture",
            )

        conditions = [
            Pictures.id_ == picture_id,
            Pictures.apartment_id == apartment_id,
            Pictures.is_deleted.is_(False),
        ]
        if apartment.main_picture:
            conditions.append(Pictures.url != apartment.main_picture)

        result = await db.execute(select(Pictures).where(*conditions))
        picture = result.scalar_one_or_none()

        if not picture:
            return False

        picture.is_deleted = True

        await db.commit()
        return True
    except Exception as e:
        logger.error(f"Error soft deleting apartment picture: {e}")
        raise e


async def is_allowed_to_create_apartment(
        db: AsyncSession, user_id: UUID) -> bool:
    try:
        user_ = await user_db.find_user_by_id(user_id, db)
        if user_:
            return user_.type_ in (UserType.AGENT, UserType.OWNER)
        return False
    except Exception as e:
        logger.error(
            f"Error checking if user is allowed to create apartment: {e}")
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

        await db.execute(
            update(Pictures)
            .where(Pictures.apartment_id == apartment_id)
            .values(is_deleted=True)
        )

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
        query = (
            select(Apartment)
            .options(selectinload(Apartment.pictures))
            .where(Apartment.owner == user_id)
        )
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

        query = (
            select(Apartment)
            .options(selectinload(Apartment.pictures))
            .where(Apartment.id_.in_(apartment_ids))
        )
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
    filter_query: FilterApartment,
    current_page: int = 1,
    page_size: int = 10
) -> List[Apartment]:
    try:
        query = select(Apartment).where(Apartment.is_deleted == False)      # noqa: E712
        data = filter_query.model_dump(exclude_unset=True)

        # Mapping logic for ranges
        if data.get("cost"):
            query = query.where(Apartment.cost.between(
                int(data["cost"] * 0.8), int(data["cost"] * 1.2)))

        if data.get("square"):
            query = query.where(
                Apartment.square.between(
                    data["square"] * 0.8,
                    data["square"] * 1.2))

        # Exact matches for non-zero/non-null values
        for field in ["renovation_type", "type_", "rooms", "floor"]:
            val = data.get(field)
            if val:
                query = query.where(getattr(Apartment, field) == val)

        # Execute with pagination
        result = await db.execute(
            query.offset((current_page - 1) * page_size).limit(page_size)
        )
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Error getting apartments by Gemini filter: {e}")
        raise e


async def get_apartment_first_photo(
    db: AsyncSession,
    apartment_id: UUID,
) -> Optional[Pictures]:
    try:
        apartment = await get_apartment(db, apartment_id)
        if not apartment:
            return None
        photo = apartment.pictures[0]
        return photo if photo else None
    except Exception as error:
        logger.error(f"Couldnt retrieve the first photo: {error}")
        raise error
