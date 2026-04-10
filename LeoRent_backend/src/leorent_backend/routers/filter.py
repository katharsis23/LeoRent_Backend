from fastapi import status, Depends, APIRouter, HTTPException
from fastapi_utils.cbv import cbv
from src.leorent_backend.database_connector import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.leorent_backend.schemas.apartment import ApartmentPreviewListResponse
from typing import List
from src.leorent_backend.models import Apartment
from fastapi.responses import JSONResponse
from loguru import logger


filter_router = APIRouter(
    prefix="/filter",
    tags=["Filter"]
)


@cbv(filter_router)
class FilterRouter:
    db: AsyncSession = Depends(get_db)

    @filter_router.get(
        path="/ai/",
        description="""
        Get Apartments based on Gemini filter
        """,
        response_model=ApartmentPreviewListResponse
    )
    async def ai_filter(
        self,
        prompt: str,
        current_page: int = 1,
        page_size: int = 10
    ) -> JSONResponse:
        try:
            pass
        except HTTPException as http_error:
            logger.error(f"HTTPException: {http_error}")
            raise http_error
