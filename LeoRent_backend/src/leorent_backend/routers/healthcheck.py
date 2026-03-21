from math import e
from fastapi_utils.cbv import cbv
from fastapi import APIRouter
from fastapi import HTTPException, status, Depends
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from leorent_backend.database import test_connection, get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from leorent_backend.models import Users
from loguru import logger


healthcheck_router = APIRouter(
    prefix="/healthcheck",
    tags=["Healthcheck"],
)


@cbv(healthcheck_router)
class HealthCheck:
    def __init__(self, request: Request):
        self.request = request

    @healthcheck_router.get(path="/",
                            response_class=JSONResponse,
                            description="""
                            Healthcheck base router for administration.
                            Returns the status of the server.
                            200 if Server is running
                            500 if Server is not running
                            """
                            )
    async def healthcheck(self):
        try:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "ok",
                    "message": "Server is running",
                },
            )
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(error),
            )

    @healthcheck_router.get(path="/db",
                            response_class=JSONResponse,
                            description="""
                            Healthcheck base router for administration.
                            Returns the status of the server.
                            200 if Server is running
                            500 if Server is not running
                            """
                            )
    async def healthcheck_db(self, db: AsyncSession = Depends(get_session)):
        try:
            await test_connection()

            # query = select(Users).limit(1)
            # result = await db.execute(query)
            # user = result.scalar_one_or_none()
            return {"status": "ok", "message": "Database is running"}
        except Exception as error:
            logger.error(f"Database healthcheck failed: {error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection error",
            )
