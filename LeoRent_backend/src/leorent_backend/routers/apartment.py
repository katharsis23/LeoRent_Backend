from fastapi_utils.cbv import cbv
from fastapi import APIRouter, Depends, status, HTTPException
from src.leorent_backend.external.firebase_auth import get_current_user
from src.leorent_backend.database_connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.leorent_backend.models import Users
from loguru import logger
from uuid import UUID
import src.leorent_backend.schemas.apartment as apartment_schemas
import src.leorent_backend.database.apartment as apartment_db
from fastapi.responses import JSONResponse


apartment_router = APIRouter(
    prefix="/apartment",
    tags=["apartment"]
)


@cbv(apartment_router)
class ApartmentController:
    db: AsyncSession = Depends(get_db)
    user_: Users = Depends(get_current_user)

    @apartment_router.get(
        path="/",
        description="Get actual apartments with pagination given as query parameters"
    )
    async def get_apartments(
        self, current_page: int = 1, page_size: int = 10
    ):
        try:
            apartments = await apartment_db.get_apartments(
                self.db, current_page, page_size
            )

            apartments_with_like_status = []
            for apartment in apartments:
                is_liked = await apartment_db.is_apartment_liked_by_user(
                    self.db, apartment.id_, self.user_.id_
                )

                apartments_with_like_status.append({
                    "id_": str(apartment.id_),
                    "title": apartment.title,
                    "cost": apartment.cost,
                    "square": apartment.square,
                    "floor": apartment.floor,
                    "rooms": apartment.rooms,
                    "floor_in_house": apartment.floor_in_house,
                    "location": apartment.location,
                    "district": apartment.district,
                    "owner_type": str(await apartment_db.get_user_type_from_apartment(
                        self.db, apartment.id_
                    )),
                    "is_liked_by_current_user": is_liked
                })

            return JSONResponse(
                content=apartments_with_like_status,
                status_code=status.HTTP_200_OK
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    @apartment_router.post(
        path="/",
        description="Create a new apartment"
    )
    async def create_apartment(
        self, apartment: apartment_schemas.ApartmentCreate
    ):
        try:
            from src.leorent_backend.models import UserType
            if self.user_.type_ not in (UserType.AGENT, UserType.OWNER):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not allowed to create an apartment"
                )

            apartment = await apartment_db.create_apartment(
                self.db, apartment, self.user_.id_
            )
            return JSONResponse(
                content={"id_": str(apartment.id_), "message": "Apartment created successfully"},
                status_code=status.HTTP_201_CREATED
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    @apartment_router.get(
        path="/{apartment_id}",
        description="Get apartment by id with full info and user details"
    )
    async def get_apartment(self, apartment_id: UUID):
        try:
            apartment = await apartment_db.get_apartment(self.db, apartment_id)

            if not apartment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Apartment not found"
                )

            owner_info = {
                "first_name": apartment.owner_user.first_name,
                "last_name": apartment.owner_user.last_name,
                "phone_number": apartment.owner_user.phone_number,
                "email": apartment.owner_user.email,
                "is_verified": apartment.owner_user.is_verified
            }

            return JSONResponse(
                content={
                    "id_": str(apartment.id_),
                    "title": apartment.title,
                    "cost": apartment.cost,
                    "square": apartment.square,
                    "floor": apartment.floor,
                    "rooms": apartment.rooms,
                    "floor_in_house": apartment.floor_in_house,
                    "location": apartment.location,
                    "district": apartment.district,
                    "description": apartment.description,
                    "details": apartment.details,
                    "rent_type": apartment.rent_type.value,
                    "type_": apartment.type_,
                    "renovation_type": apartment.renovation_type,
                    "owner": owner_info
                },
                status_code=status.HTTP_200_OK
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    @apartment_router.put(
        path="/{apartment_id}",
        description="Update an existing apartment"
    )
    async def update_apartment(
        self, apartment_id: UUID, apartment_update: apartment_schemas.ApartmentUpdate
    ):
        try:
            apartment = await apartment_db.update_apartment(
                self.db, apartment_id, apartment_update, self.user_.id_
            )

            if not apartment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Apartment not found"
                )

            return JSONResponse(
                content={"id_": str(apartment.id_), "message": "Apartment updated successfully"},
                status_code=status.HTTP_200_OK
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    @apartment_router.delete(
        path="/{apartment_id}",
        description="Soft delete an apartment"
    )
    async def delete_apartment(self, apartment_id: UUID):
        try:
            success = await apartment_db.delete_apartment(
                self.db, apartment_id, self.user_.id_
            )

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Apartment not found"
                )

            return JSONResponse(
                content={"message": "Apartment deleted successfully"},
                status_code=status.HTTP_204_NO_CONTENT
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error
