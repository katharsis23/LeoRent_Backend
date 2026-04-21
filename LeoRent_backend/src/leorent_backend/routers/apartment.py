import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

import src.leorent_backend.database.apartment as apartment_db
import src.leorent_backend.schemas.apartment as apartment_schemas
from src.leorent_backend.database_connector import get_db
from src.leorent_backend.external.firebase_auth import get_current_user, get_optional_user
from src.leorent_backend.models import Users
from src.leorent_backend.services.backblaze_service import backblaze_service


MAX_PHOTO_SIZE_BYTES = 10 * 1024 * 1024


apartment_router = APIRouter(
    prefix="/apartment",
    tags=["apartment"]
)


def _get_picture_urls(apartment) -> list[str]:
    if not apartment.main_picture:
        return []
    return [apartment.main_picture]


def _serialize_picture_records(apartment) -> list[dict[str, Any]]:
    return [
        {
            "id_": str(picture.id_),
            "url": picture.url,
            "metadata": {
                key: value
                for key, value in (picture.metadata_ or {}).items()
                if key != "is_main"
            },
        }
        for picture in apartment.pictures
        if not picture.is_deleted and picture.url != apartment.main_picture
    ]


def _build_picture_key(user_id: UUID, file_name: str) -> str:
    file_suffix = Path(file_name.split("?", 1)[0]).suffix or ".jpg"
    return f"apartments/{user_id}/{uuid4()}{file_suffix.lower()}"


def _ensure_photo_size_limit(file_name: str, size_bytes: int) -> None:
    if size_bytes > MAX_PHOTO_SIZE_BYTES:
        raise ValueError(
            f"File {file_name} exceeds the 10 MB limit."
        )


def _detect_picture_format(
    *,
    file_name: str | None = None,
    content_type: str | None = None,
) -> str | None:
    normalized_file_name = str(file_name or "").strip()
    if normalized_file_name:
        file_suffix = Path(
            normalized_file_name.split("?", 1)[0]
        ).suffix.lower().lstrip(".")
        if file_suffix:
            return file_suffix

    normalized_content_type = (
        (content_type or "").split(";", 1)[0].strip().lower()
    )
    if normalized_content_type.startswith("image/"):
        return normalized_content_type.split("/", 1)[1]

    return None


def _merge_picture_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    file_name: str | None = None,
    content_type: str | None = None,
    size_bytes: int | None = None,
) -> dict[str, Any]:
    normalized_metadata = {
        key: value
        for key, value in dict(metadata or {}).items()
        if key != "is_main"
    }

    picture_format = _detect_picture_format(
        file_name=file_name,
        content_type=content_type,
    )
    if picture_format:
        normalized_metadata["format"] = picture_format

    if size_bytes is not None:
        normalized_metadata["size_bytes"] = size_bytes

    return normalized_metadata


async def _parse_create_apartment_request(
    request: Request,
) -> tuple[apartment_schemas.ApartmentCreate, list[object]]:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        payload = await request.json()
        return apartment_schemas.ApartmentCreate.model_validate(payload), []

    form = await request.form()
    payload: dict[str, object] = {}
    main_pictures: list[str] = []
    uploaded_files: list[object] = []

    for key, value in form.multi_items():
        if hasattr(value, "filename") and hasattr(value, "read"):
            if key in {"main_pictures_files", "main_picture_files", "files"}:
                uploaded_files.append(value)
            continue

        if key == "main_pictures":
            normalized_value = str(value).strip()
            if normalized_value:
                main_pictures.append(normalized_value)
            continue

        payload[key] = value

    if main_pictures:
        payload["main_pictures"] = main_pictures

    details = payload.get("details")
    if isinstance(details, str) and details.strip():
        try:
            payload["details"] = json.loads(details)
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="details must be valid JSON.",
            ) from error

    apartment = apartment_schemas.ApartmentCreate.model_validate(payload)
    return apartment, uploaded_files


async def _upload_main_pictures(
    user_id: UUID,
    apartment: apartment_schemas.ApartmentCreate,
    uploaded_files: list[object],
) -> list[dict[str, Any]]:
    saved_pictures: list[dict[str, Any]] = []

    for picture_source in apartment.main_pictures or []:
        s3_key = _build_picture_key(user_id, picture_source)
        upload_result = await backblaze_service.upload_photo_from_source_details(
            source=picture_source,
            s3_key=s3_key,
        )
        saved_pictures.append(
            {
                "url": upload_result["url"],
                "metadata": _merge_picture_metadata(
                    file_name=s3_key,
                    content_type=upload_result.get("content_type"),
                    size_bytes=upload_result.get("size_bytes"),
                ),
            }
        )

    for uploaded_file in uploaded_files:
        read_method = getattr(uploaded_file, "read", None)
        if not callable(read_method):
            continue

        file_bytes = await read_method()
        if not file_bytes:
            continue

        file_name = getattr(uploaded_file, "filename", "image.jpg")
        _ensure_photo_size_limit(file_name, len(file_bytes))
        content_type = getattr(
            uploaded_file,
            "content_type",
            "application/octet-stream",
        )
        s3_key = _build_picture_key(user_id, file_name or "image.jpg")

        url = await backblaze_service.upload_photo_from_bytes(
            data=file_bytes,
            s3_key=s3_key,
            content_type=content_type or "application/octet-stream",
        )
        saved_pictures.append(
            {
                "url": url,
                "metadata": _merge_picture_metadata(
                    file_name=s3_key,
                    content_type=content_type,
                    size_bytes=len(file_bytes),
                ),
            }
        )

    unique_pictures: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for picture in saved_pictures:
        url = picture["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        unique_pictures.append(picture)

    for picture in unique_pictures:
        picture["metadata"] = _merge_picture_metadata(
            picture.get("metadata"),
        )

    return unique_pictures


def _parse_metadata_items(
    metadata_inputs: list[object],
    total_pictures: int,
) -> list[dict[str, Any]]:
    if not metadata_inputs:
        return [{} for _ in range(total_pictures)]

    if len(metadata_inputs) == 1 and isinstance(metadata_inputs[0], str):
        raw_value = metadata_inputs[0].strip()
        if raw_value.startswith("[") and raw_value.endswith("]"):
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="metadata must be valid JSON.",
                ) from error
            if not isinstance(parsed, list):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="metadata must be a JSON array.",
                )
            metadata_list = [
                item if isinstance(item, dict) else {}
                for item in parsed
            ]
        else:
            metadata_list = [json.loads(raw_value)] if raw_value else [{}]
    else:
        metadata_list = []
        for raw_item in metadata_inputs:
            if isinstance(raw_item, str) and raw_item.strip():
                try:
                    parsed_item = json.loads(raw_item)
                except json.JSONDecodeError as error:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="metadata must be valid JSON.",
                    ) from error
                metadata_list.append(
                    parsed_item if isinstance(parsed_item, dict) else {}
                )
            else:
                metadata_list.append({})

    if len(metadata_list) > total_pictures:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="metadata count exceeds number of pictures.",
        )

    while len(metadata_list) < total_pictures:
        metadata_list.append({})

    return metadata_list


async def _parse_picture_upload_request(
    request: Request,
) -> list[dict[str, Any]]:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        payload = await request.json()
        pictures = payload.get("pictures", [])
        if not isinstance(pictures, list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="pictures must be a list.",
            )

        normalized_pictures: list[dict[str, Any]] = []
        for picture in pictures:
            if not isinstance(picture, dict):
                continue
            source = str(picture.get("source", "")).strip()
            if not source:
                continue
            metadata = picture.get("metadata") or {}
            normalized_pictures.append(
                {
                    "source": source,
                    "metadata": metadata if isinstance(metadata, dict) else {},
                }
            )
        return normalized_pictures

    form = await request.form()
    picture_inputs: list[dict[str, Any]] = []
    metadata_inputs: list[object] = []

    for key, value in form.multi_items():
        if hasattr(value, "filename") and hasattr(value, "read"):
            if key in {"picture_files", "pictures_files", "files"}:
                picture_inputs.append({"upload_file": value})
            continue

        if key in {"picture_urls", "picture_url"}:
            normalized_value = str(value).strip()
            if normalized_value:
                picture_inputs.append({"source": normalized_value})
            continue

        if key in {"metadata", "picture_metadata"}:
            metadata_inputs.append(value)

    metadata_list = _parse_metadata_items(metadata_inputs, len(picture_inputs))
    for index, metadata in enumerate(metadata_list):
        if index < len(picture_inputs):
            picture_inputs[index]["metadata"] = metadata

    return picture_inputs


async def _upload_picture_entries(
    user_id: UUID,
    picture_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    saved_pictures: list[dict[str, Any]] = []

    for picture_entry in picture_entries:
        metadata = picture_entry.get("metadata") or {}

        if "source" in picture_entry:
            picture_source = str(picture_entry["source"])
            s3_key = _build_picture_key(user_id, picture_source)
            upload_result = await backblaze_service.upload_photo_from_source_details(
                source=picture_source,
                s3_key=s3_key,
            )
            url = upload_result["url"]
            metadata = _merge_picture_metadata(
                metadata,
                file_name=s3_key,
                content_type=upload_result.get("content_type"),
                size_bytes=upload_result.get("size_bytes"),
            )
        else:
            uploaded_file = picture_entry.get("upload_file")
            read_method = getattr(uploaded_file, "read", None)
            if not callable(read_method):
                continue

            file_bytes = await read_method()
            if not file_bytes:
                continue

            file_name = getattr(uploaded_file, "filename", "image.jpg")
            _ensure_photo_size_limit(file_name, len(file_bytes))
            content_type = getattr(
                uploaded_file,
                "content_type",
                "application/octet-stream",
            )
            s3_key = _build_picture_key(user_id, file_name or "image.jpg")
            url = await backblaze_service.upload_photo_from_bytes(
                data=file_bytes,
                s3_key=s3_key,
                content_type=content_type or "application/octet-stream",
            )
            metadata = _merge_picture_metadata(
                metadata,
                file_name=s3_key,
                content_type=content_type,
                size_bytes=len(file_bytes),
            )

        saved_pictures.append({"url": url, "metadata": metadata})

    return saved_pictures


@cbv(apartment_router)
class ApartmentController:
    db: AsyncSession = Depends(get_db)

    @apartment_router.get(
        path="/",
        description="Get actual apartments with pagination given as query parameters",
    )
    async def get_apartments(
        self,
        current_page: int = 1,
        page_size: int = 6,
        district: str | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        rooms: str | None = None,
        square_min: float | None = None,
        square_max: float | None = None,
        floor_min: int | None = None,
        floor_max: int | None = None,
        rent_type: str | None = None,
        owner_type: str | None = None,
        sort: str = "newest",
        user_: Users | None = Depends(get_optional_user)
    ):
        try:
            filters = {
                "district": district,
                "price_min": price_min,
                "price_max": price_max,
                "rooms": [int(r) for r in rooms.split(",")] if rooms else None,
                "square_min": square_min,
                "square_max": square_max,
                "floor_min": floor_min,
                "floor_max": floor_max,
                "rent_type": rent_type,
                "owner_type": owner_type,
            }

            apartments, total = await apartment_db.get_apartments(
                self.db, current_page, page_size, filters, sort
            )
            logger.debug(f"DB total: {total}, count: {len(apartments)}")

            apartments_with_like_status = []
            for apartment in apartments:
                is_liked = False
                if user_:
                    is_liked = await apartment_db.is_apartment_liked_by_user(
                        self.db, apartment.id_, user_.id_
                    )

                owner_type_val = await apartment_db.get_user_type_from_apartment(
                    self.db, apartment.id_
                )

                apartments_with_like_status.append(
                    apartment_schemas.ApartmentPreviewResponse(
                        id_=apartment.id_,
                        title=apartment.title,
                        cost=apartment.cost,
                        rooms=apartment.rooms,
                        square=apartment.square,
                        floor=apartment.floor,
                        floor_in_house=apartment.floor_in_house,
                        rent_type=apartment.rent_type.value,
                        type_=apartment.type_,
                        renovation_type=apartment.renovation_type,
                        location=apartment.location,
                        district=apartment.district,
                        owner_type=str(owner_type_val.value) if owner_type_val else "DEFAULT",
                        is_liked_by_current_user=is_liked,
                        picture=apartment.pictures[0].url if apartment.pictures else None
                    )
                )

            response_data = apartment_schemas.ApartmentPreviewListResponse(
                apartments=apartments_with_like_status,
                total=total,
                page=current_page,
                page_size=page_size,
            ).model_dump(mode="json")

            logger.debug(f"Response total: {response_data.get('total')}")

            return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in get_apartments: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @apartment_router.post(
        path="/",
        description="Create a new apartment"
    )
    async def create_apartment(
        self,
        request: Request,
        user_: Users = Depends(get_current_user)
    ):
        try:
            from src.leorent_backend.models import UserType
            if user_.type_ not in (UserType.AGENT, UserType.OWNER):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not allowed to create an apartment"
                )

            apartment, uploaded_files = await _parse_create_apartment_request(
                request
            )
            saved_pictures = await _upload_main_pictures(
                user_.id_, apartment, uploaded_files
            )

            apartment = await apartment_db.create_apartment(
                self.db,
                apartment,
                user_.id_,
                pictures=saved_pictures,
            )
            return JSONResponse(
                content={
                    "id_": str(apartment.id_),
                    "message": "Apartment created successfully",
                    "main_pictures": _get_picture_urls(apartment),
                    "pictures": _serialize_picture_records(apartment),
                },
                status_code=status.HTTP_201_CREATED
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error
        except ValueError as value_error:
            logger.error(f"ValueError: {value_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(value_error),
            ) from value_error

    @apartment_router.post(
        path="/{apartment_id}/pictures",
        description="Add multiple pictures to an apartment"
    )
    async def add_apartment_pictures(
        self,
        apartment_id: UUID,
        request: Request,
        user_: Users = Depends(get_current_user)
    ):
        try:
            apartment = await apartment_db.get_apartment(self.db, apartment_id)

            if not apartment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Apartment not found",
                )

            if apartment.owner != user_.id_:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the apartment owner can add pictures",
                )

            picture_entries = await _parse_picture_upload_request(request)
            if not picture_entries:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="At least one picture URL or file is required.",
                )

            saved_pictures = await _upload_picture_entries(
                user_.id_,
                picture_entries,
            )
            apartment = await apartment_db.add_apartment_pictures(
                self.db,
                apartment_id,
                saved_pictures,
            )

            return JSONResponse(
                content={
                    "apartment_id": str(apartment.id_),
                    "pictures": _serialize_picture_records(apartment),
                },
                status_code=status.HTTP_201_CREATED,
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error
        except ValueError as value_error:
            logger.error(f"ValueError: {value_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(value_error),
            ) from value_error

    @apartment_router.delete(
        path="/{apartment_id}/pictures",
        description="Soft delete all apartment pictures"
    )
    async def delete_all_apartment_pictures(
        self,
        apartment_id: UUID,
        user_: Users = Depends(get_current_user)
    ):
        try:
            success = await apartment_db.soft_delete_all_apartment_pictures(
                self.db,
                apartment_id,
                user_.id_,
            )

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Apartment not found",
                )

            return JSONResponse(
                content={
                    "success": True,
                    "message": "All apartment pictures deleted",
                },
                status_code=status.HTTP_200_OK,
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    @apartment_router.delete(
        path="/{apartment_id}/pictures/{picture_id}",
        description="Soft delete a single apartment picture"
    )
    async def delete_apartment_picture(
        self,
        apartment_id: UUID,
        picture_id: UUID,
        user_: Users = Depends(get_current_user)
    ):
        try:
            success = await apartment_db.soft_delete_apartment_picture(
                self.db,
                apartment_id,
                picture_id,
                user_.id_,
            )

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Picture not found",
                )

            return JSONResponse(
                content={"success": True, "message": "Picture deleted"},
                status_code=status.HTTP_200_OK,
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    @apartment_router.get(
        path="/{apartment_id}",
        description="Get apartment by id with full info and user details"
    )
    async def get_apartment(
        self,
        apartment_id: UUID,
        user_: Users | None = Depends(get_optional_user)
    ):
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
                content=apartment_schemas.ApartmentFullInfoResponse(
                    id_=apartment.id_,
                    title=apartment.title,
                    description=apartment.description,
                    location=apartment.location,
                    district=apartment.district,
                    cost=apartment.cost,
                    rent_type=apartment.rent_type.value,
                    rooms=apartment.rooms,
                    square=apartment.square,
                    floor=apartment.floor,
                    floor_in_house=apartment.floor_in_house,
                    details=apartment.details,
                    type_=apartment.type_,
                    renovation_type=apartment.renovation_type,
                    pictures=_serialize_picture_records(apartment),
                    owner_type=str(apartment.owner_user.type_.value),
                    owner_info=owner_info
                ).model_dump(mode="json"),
                status_code=status.HTTP_200_OK
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    # IMPROVE:  Return Apartment info instead of id_
    @apartment_router.put(
        path="/{apartment_id}",
        description="Update an existing apartment"
    )
    async def update_apartment(
            self,
            apartment_id: UUID,
            apartment_update: apartment_schemas.ApartmentUpdate,
            user_: Users = Depends(get_current_user)):
        try:
            apartment = await apartment_db.update_apartment(
                self.db, apartment_id, apartment_update, user_.id_
            )

            if not apartment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Apartment not found"
                )

            return JSONResponse(
                content={
                    "id_": str(
                        apartment.id_),
                    "message": "Apartment updated successfully"},
                status_code=status.HTTP_200_OK)
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    @apartment_router.delete(
        path="/{apartment_id}",
        description="Soft delete an apartment"
    )
    async def delete_apartment(
        self,
        apartment_id: UUID,
        user_: Users = Depends(get_current_user)
    ):
        try:
            success = await apartment_db.delete_apartment(
                self.db, apartment_id, user_.id_
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

    @apartment_router.get(
        path="/my/",
        description="""
        Get apartments for current user if its Agent or Owner
        Returns in pagination
        """,
        response_model=apartment_schemas.ApartmentListResponse
    )
    async def get_my_apartments(
        self,
        current_page: int = 1,
        page_size: int = 30,
        user_: Users = Depends(get_current_user)
    ):
        try:
            apartments = await apartment_db.get_apartments_by_user(
                self.db, user_.id_, current_page, page_size
            )

            # Use Pydantic schema for serialization
            serialized_apartments = [
                apartment_schemas.ApartmentResponse(
                    id_=apartment.id_,
                    title=apartment.title,
                    description=apartment.description,
                    location=apartment.location,
                    district=apartment.district,
                    cost=apartment.cost,
                    rent_type=apartment.rent_type.value,
                    is_deleted=apartment.is_deleted,
                    rooms=apartment.rooms,
                    square=apartment.square,
                    floor=apartment.floor,
                    floor_in_house=apartment.floor_in_house,
                    details=apartment.details,
                    type_=apartment.type_,
                    renovation_type=apartment.renovation_type,
                    pictures=_serialize_picture_records(apartment),
                    owner=apartment.owner
                ) for apartment in apartments
            ]

            return JSONResponse(
                content=apartment_schemas.ApartmentListResponse(
                    apartments=serialized_apartments
                ).model_dump(mode="json"),
                status_code=status.HTTP_200_OK
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error

    @apartment_router.post(
        path="/{apartment_id}/like",
        description="Toggle like/unlike for an apartment",
        response_model=apartment_schemas.ApartmentLikeResponse
    )
    async def toggle_like_apartment(
        self,
        apartment_id: UUID,
        user_: Users = Depends(get_current_user)
    ):
        try:
            result = await apartment_db.toggle_like_apartment(
                self.db, apartment_id, user_.id_
            )

            if "error" in result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result["error"]
                )

            return JSONResponse(
                content=apartment_schemas.ApartmentLikeResponse(
                    message=result["message"],
                    status=result["action"]
                ).model_dump(mode="json"),
                status_code=status.HTTP_200_OK
            )
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error
        except Exception as e:
            logger.error(f"Error toggling like for apartment: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error toggling like for apartment"
            )

    @apartment_router.get(
        path="/liked/",
        description="Get liked apartments",
        response_model=apartment_schemas.ApartmentListResponse
    )
    async def get_liked_apartments(
        self,
        user_: Users = Depends(get_current_user)
    ):
        try:
            liked_apartments = await apartment_db.get_liked_apartments_by_user(
                self.db, user_.id_
            )

            # Use Pydantic schema for serialization
            serialized_apartments = [
                apartment_schemas.ApartmentResponse(
                    id_=apartment.id_,
                    title=apartment.title,
                    description=apartment.description,
                    location=apartment.location,
                    district=apartment.district,
                    cost=apartment.cost,
                    rent_type=apartment.rent_type.value,
                    is_deleted=apartment.is_deleted,
                    rooms=apartment.rooms,
                    square=apartment.square,
                    floor=apartment.floor,
                    floor_in_house=apartment.floor_in_house,
                    details=apartment.details,
                    type_=apartment.type_,
                    renovation_type=apartment.renovation_type,
                    pictures=_serialize_picture_records(apartment),
                    owner=apartment.owner
                ) for apartment in liked_apartments
            ]

            return JSONResponse(
                content=apartment_schemas.ApartmentListResponse(
                    apartments=serialized_apartments
                ).model_dump(mode="json"),
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error getting liked apartments: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error getting liked apartments"
            )
