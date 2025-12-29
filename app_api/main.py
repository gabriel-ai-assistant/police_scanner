from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from database import get_pool, close_pool
from routers import health, calls, playlists, transcripts, analytics, geography, system, auth
from auth.firebase import initialize_firebase


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting up Police Scanner API...")
    await get_pool()
    logger.info("Database connection pool created")

    # Initialize Firebase Auth
    if initialize_firebase():
        logger.info("Firebase Admin SDK initialized")
    else:
        logger.warning("Firebase Admin SDK not initialized - authentication disabled")

    yield
    # Shutdown
    logger.info("Shutting down Police Scanner API...")
    await close_pool()
    logger.info("Database connection pool closed")


app = FastAPI(
    title="Police Scanner API",
    description="REST API for Police Scanner frontend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(auth.admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(playlists.router, prefix="/api/playlists", tags=["Playlists"])
app.include_router(transcripts.router, prefix="/api/transcripts", tags=["Transcripts"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(geography.router, prefix="/api/geography", tags=["Geography"])
app.include_router(system.router, prefix="/api/system", tags=["System"])


@app.get("/")
async def root():
    return {"message": "Police Scanner API", "version": "1.0.0"}
