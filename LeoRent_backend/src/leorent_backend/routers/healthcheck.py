from fastapi_utils.cbv import cbv
from fastapi import APIRouter
from fastapi import HTTPException, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from leorent_backend.database import test_connection

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
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
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
    async def healthcheck_db(self):
        try:
            await test_connection()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "ok",
                    "message": "Database is running",
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
