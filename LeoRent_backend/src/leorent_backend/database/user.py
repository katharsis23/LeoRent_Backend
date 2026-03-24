from src.leorent_backend.models import Users
from src.leorent_backend.schemas.user import CreateUser, LoginUser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import bcrypt
from uuid import UUID
from typing import Optional
from loguru import logger

# from fastapi import HTTPException, status
# from fastapi.responses import JSONResponse


async def find_user_by_id(user: UUID, db: AsyncSession) -> Optional[Users]:
    try:
        query = await db.execute(select(Users).where(Users.id == user))
        return query.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"Error finding user by id: {e}")
        return None


async def create_user(user: CreateUser, db: AsyncSession) -> Optional[Users]:
    try:
        # Check on Phone number, Email and Username uniqueness
        user_with_duplicate_fields = await db.execute(
            select(Users).where(
                (Users.username == user.username)
                | (Users.email == user.email)
                | (Users.phone_number == user.phone)
            )
        )
        if user_with_duplicate_fields.scalar_one_or_none():

            return None
        password = bcrypt.hashpw(
            user.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        new_user = Users(
            username=user.username,
            email=user.email,
            phone_number=user.phone,
            password=password,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except SQLAlchemyError as e:
        logger.error(f"Error creating user: {e}")
        return None


async def login_user(user: LoginUser, db: AsyncSession) -> Optional[Users]:
    try:
        query = await db.execute(select(Users).where(Users.email == user.email))
        existing_user = query.scalar_one_or_none()

        if not existing_user:
            return None

        if not bcrypt.checkpw(
            user.password.encode(
                "utf-8"), existing_user.password.encode("utf-8")
        ):
            return None
        return existing_user

    except SQLAlchemyError as e:
        logger.error(f"Error logging in user: {e}")
        return None
