from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from contextlib import asynccontextmanager
# Routers
from src.leorent_backend.routers.healthcheck import healthcheck_router
from src.leorent_backend.database_connector import BASE, engine
from src.leorent_backend.routers.user import user_router


# Change in the future with table metadata adding

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Server is starting...")
        logger.debug("CREATING TABLES")
        async with engine.begin() as conn:
            await conn.run_sync(BASE.metadata.create_all)
        logger.debug("TABLES CREATED")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
    yield
    logger.info("Server is shutting down...")


app = FastAPI(
    title="LeoRent Backend",
    description="""
    Backend part of LeoRent App.
    Real Estate Platform that ensures safe and transparent rental process for
    both landlords and tenants.
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "LeoRent Backend is running! ♡", "docs": "/docs"}


app.include_router(healthcheck_router)
app.include_router(user_router)
