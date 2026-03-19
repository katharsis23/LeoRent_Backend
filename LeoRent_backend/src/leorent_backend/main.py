from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from contextlib import asynccontextmanager
# Routers
from src.leorent_backend.routers.healthcheck import healthcheck_router
from src.leorent_backend.database import BASE, engine
import sys


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
        BASE.metadata.create_all(bind=engine)
        logger.debug("TABLES CREATED")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)
    yield
    logger.info("Server is shutting down...")


app.include_router(healthcheck_router)
