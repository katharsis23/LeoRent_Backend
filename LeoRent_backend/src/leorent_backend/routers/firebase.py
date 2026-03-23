from fastapi_utils.cbv import cbv
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from src.leorent_backend.external.firebase_auth import get_current_user
from src.leorent_backend.models import Users
from sqlalchemy.ext.asyncio import AsyncSession


from src.leorent_backend.database_connector import get_db

firebase_router = APIRouter(
    prefix="/firebase",
    tags=["Firebase Authentication"],
)


@cbv(firebase_router)
class FirebaseAuthRouter:
    db: AsyncSession = Depends(get_db)

    @firebase_router.post(path="/signup", description="""
    Firebase-based user signup/registration.
    Creates or updates user from Firebase token.
    """)
    async def firebase_signup(self, current_user: Users = Depends(get_current_user)):
        try:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Firebase user authenticated successfully",
                    "user": {
                        "id": str(current_user.id_),
                        "email": current_user.email,
                        "username": current_user.username,
                        "first_name": current_user.first_name,
                        "last_name": current_user.last_name,
                        "phone": current_user.phone_number,
                        "user_type": current_user.type_.value,
                        "is_verified": current_user.is_verified,
                        "firebase_uid": current_user.firebase_uid,
                    }
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @firebase_router.get(path="/me", description="""
    Get current authenticated user profile from Firebase token.
    """)
    async def get_profile(self, current_user: Users = Depends(get_current_user)):
        try:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "user": {
                        "id": str(current_user.id_),
                        "email": current_user.email,
                        "username": current_user.username,
                        "first_name": current_user.first_name,
                        "last_name": current_user.last_name,
                        "phone": current_user.phone_number,
                        "user_type": current_user.type_.value,
                        "is_verified": current_user.is_verified,
                        "firebase_uid": current_user.firebase_uid,
                    }
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
