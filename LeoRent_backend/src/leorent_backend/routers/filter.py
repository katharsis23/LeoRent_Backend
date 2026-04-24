from fastapi import status, Depends, APIRouter, Query
from fastapi_utils.cbv import cbv
from src.leorent_backend.database_connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.leorent_backend.schemas.apartment import ApartmentPreviewListResponse, ApartmentPreviewResponse
from fastapi.responses import JSONResponse
from loguru import logger
import src.leorent_backend.schemas.filter as filter_schema
from src.leorent_backend.database.apartment import get_apartments_by_gemini_filter
from src.leorent_backend.external.gemini_client import GeminiClient
from src.leorent_backend.external.groq_client import GroqClient


filter_router = APIRouter(
    prefix="/filter",
    tags=["Filter"]
)


@cbv(filter_router)
class FilterRouter:
    db: AsyncSession = Depends(get_db)
    gemini_client = GeminiClient()
    groq_client = GroqClient()

    @filter_router.get("/ai-search")
    async def search_apartments_by_prompt(
        self,
        prompt: str = Query(...),
        page: int = Query(1),
        size: int = Query(10),
        db: AsyncSession = Depends(get_db)
    ):
        try:
            # 1. Get dictionary from Gemini
            filter_data = await self.gemini_client.generate_json(prompt)

            try:
                # 2. Validate with Pydantic Filter
                apartment_filter = filter_schema.FilterApartment(**filter_data)
            except Exception as parse_error:
                logger.error(f"Pydantic validation failed: {parse_error}")
                return JSONResponse(
                    status_code=422, content={
                        "detail": "AI output didn't match internal filter schema."})

            # 3. DB Query (returns List[Apartment] models)
            apartments_db = await get_apartments_by_gemini_filter(
                db=db,
                filter_query=apartment_filter,
                current_page=page,
                page_size=size
            )
            logger.info(f"DB response: {apartments_db}")

            apartments = [
                ApartmentPreviewResponse(
                        id_=str(apartment.id_),
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
                        owner_type=str(apartment.owner_user.type_.value) if apartment.owner_user.type_.value else None,
                        is_liked_by_current_user=False,
                        created_at=apartment.created_at,
                        picture=apartment.pictures[0].url if apartment.pictures else "https://leorent-photos.s3.eu-central-003.backblazeb2.com/apartments/default/default.jpg"
                ).model_dump(mode="json") for apartment in apartments_db
            ]

            # 4. Wrap into the response schema
            # We use list comprehension to ensure every DB model is validated
            # Ensure your ApartmentPreviewResponse has 'from_attributes = True'
            # in its Config
            logger.info(f"Response data: {apartments}")

            # 5. Return as JSONResponse
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "apartments": apartments
                }
            )

        except Exception as e:
            logger.error(f"Error searching apartments by prompt: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to search apartments."}
            )

    @filter_router.get("/ai-prompt/groq")
    async def get_groq_prompt(
        self,
        prompt: str = Query(...),
        db: AsyncSession = Depends(get_db),
        page_size: int = 6,
        current_page: int = 1
    ):
        try:
            ai_response = await self.groq_client.generate_json(prompt)
            try:
                # 2. Validate with Pydantic Filter
                apartment_filter = filter_schema.FilterApartment(**ai_response)
            except Exception as parse_error:
                logger.error(f"Pydantic validation failed: {parse_error}")
                return JSONResponse(
                    status_code=422, content={
                        "detail": "AI output didn't match internal filter schema."})

            apartments_db = await get_apartments_by_gemini_filter(
                db=db,
                filter_query=apartment_filter,
                current_page=current_page,
                page_size=page_size
            )
            apartments = [
                ApartmentPreviewResponse(
                        id_=str(apartment.id_),
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
                        owner_type=str(apartment.owner_user.type_.value) if apartment.owner_user.type_.value else None,
                        is_liked_by_current_user=False,
                        created_at=apartment.created_at,
                        picture=apartment.pictures[0].url if apartment.pictures else "https://leorent-photos.s3.eu-central-003.backblazeb2.com/apartments/default/default.jpg"
                ).model_dump(mode="json") for apartment in apartments_db
            ]

            # 4. Wrap into the response schema
            # We use list comprehension to ensure every DB model is validated
            # Ensure your ApartmentPreviewResponse has 'from_attributes = True'
            # in its Config
            logger.info(f"Response data: {apartments}")

            # 5. Return as JSONResponse
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "apartments": apartments
                }
            )
        except Exception as e:
            logger.error(f"Error getting Groq prompt: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to get Groq prompt."}
            )
