from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from contextlib import asynccontextmanager

#Middlewares
from src.leorent_backend.middleware.logging import LoggingMiddleware, ErrorHandlingMiddleware
from src.leorent_backend.middleware.rate_limiter import RateLimitMiddleware
from src.leorent_backend.redis_client import redis_client

# Routers
from src.leorent_backend.routers.healthcheck import healthcheck_router
from src.leorent_backend.database_connector import BASE, engine
from src.leorent_backend.routers.user import user_router
from src.leorent_backend.routers.photos import photo_router
from src.leorent_backend.routers.firebase import firebase_router


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


# Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    redis_client=redis_client,
    limit=30,
    window=60
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

app.include_router(photo_router)
app.include_router(healthcheck_router)
app.include_router(user_router)
app.include_router(firebase_router)
