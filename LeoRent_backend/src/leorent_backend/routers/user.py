from fastapi_utils.cbv import cbv
from fastapi import APIRouter
from fastapi import HTTPException, status, Depends
from fastapi.responses import JSONResponse
from src.leorent_backend.database.user import create_user, login_user
from src.leorent_backend.schemas.user import CreateUser, LoginUser
from src.leorent_backend.database_connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession

user_router = APIRouter(
    prefix="/users",
    tags=["User"],
)


@cbv(user_router)
class UserRouter:
    db: AsyncSession = Depends(get_db)

    @user_router.post(
        path="/signup/v1",
        description="""
    Version 1 of the signup endpoint. Easy stub and may be insecure
    Does not support firebase authentication
    """,
    )
    async def create_user(self, user: CreateUser):
        try:
            new_user = await create_user(db=self.db, user=user)
            if new_user is None:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": "User with duplicate fields"},
                )
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "id": str(new_user.id_),
                    "email": new_user.email,
                    "username": new_user.username,
                    "phone": new_user.phone_number,
                    "user_type": new_user.type_.value,
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(
                    e)
            )

    @user_router.post(
        path="/login/v1",
        description="""
    Version 1 of the login endpoint. Easy stub and may be insecure
    Does not support firebase authentication
    """,
    )
    async def login_user(self, user: LoginUser):
        try:
            existing_user = await login_user(db=self.db, user=user)
            if existing_user is None:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": "Invalid credentials"},
                )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "id": str(existing_user.id_),
                    "email": existing_user.email,
                    "username": existing_user.username,
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(
                    e)
            )
