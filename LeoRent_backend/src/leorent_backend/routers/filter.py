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


filter_router = APIRouter(
    prefix="/filter",
    tags=["Filter"]
)


@cbv(filter_router)
class FilterRouter:
    db: AsyncSession = Depends(get_db)
    gemini_client = GeminiClient()

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

            # 4. Wrap into the response schema
            # We use list comprehension to ensure every DB model is validated
            # Ensure your ApartmentPreviewResponse has 'from_attributes = True'
            # in its Config
            response_data = ApartmentPreviewListResponse(
                apartments=[
                    ApartmentPreviewResponse.model_validate(apt, from_attributes=True)
                    for apt in apartments_db
                ]
            )
            logger.info(f"Response data: {response_data}")

            # 5. Return as JSONResponse
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response_data.model_dump(mode="json")
            )

        except Exception as e:
            logger.error(f"Error searching apartments by prompt: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Failed to search apartments."}
            )
