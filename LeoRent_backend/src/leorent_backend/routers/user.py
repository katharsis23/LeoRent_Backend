from fastapi_utils.cbv import cbv
from fastapi import APIRouter
from fastapi import HTTPException, status, Depends
from fastapi.responses import JSONResponse
from src.leorent_backend.database.user import create_user, login_user
from src.leorent_backend.schemas.user import CreateUser, LoginUser
from src.leorent_backend.schemas.auth import FirebaseAuthRequest
from src.leorent_backend.database_connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.leorent_backend.external.firebase_auth import get_current_user
from src.leorent_backend.models import Users

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

    @user_router.post(path="/firebase-auth/v1", description="""
    Firebase authentication endpoint v1
    Supports Email/Password and Google providers
    Accepts Firebase ID token and returns user information
    """)
    async def firebase_auth(
            self, request: FirebaseAuthRequest) -> JSONResponse:
        try:
            # Create a temporary credentials object from the token
            from fastapi.security import HTTPAuthorizationCredentials
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=request.id_token
            )

            # Use get_current_user to authenticate and get/create user
            user = await get_current_user(credentials=credentials, db=self.db)

            if not user:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "message": "Authentication failed"
                    }
                )

            # Return user information
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "id": str(user.id_),
                    "email": user.email,
                    "username": user.username,
                    "phone_number": user.phone_number,
                    "user_type": user.type_.value,
                    "firebase_uid": user.firebase_uid,
                    "is_verified": user.is_verified,
                }
            )

        except HTTPException:
            # Re-raise HTTP exceptions from get_current_user
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
