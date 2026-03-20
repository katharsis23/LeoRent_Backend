from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from contextlib import asynccontextmanager
# Routers
from leorent_backend.routers.healthcheck import healthcheck_router
from leorent_backend.database import BASE, engine
import sys  # Keep for potential future use or just remove ♡
# sys is not really needed here if it's commented out later, but I'll just remove the unused line to make it cleaner! ♡


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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        # sys.exit(1)  # Optional: depends on if we want to kill host
    yield
    logger.info("Server is shutting down...")


@app.get("/", tags=["Root"])
async def root():
    return {"message": "LeoRent Backend is running! ♡", "docs": "/docs"}


app.include_router(healthcheck_router)
