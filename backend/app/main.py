"""
Videogen-Lucy AI Long-Form Video Generation Platform - FastAPI Application Entry Point.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.models.database import init_db
from backend.app.api.v1.router import api_v1_router

logger = logging.getLogger("videogen")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize storage directories and database tables
    settings.init_directories()
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-Ready AI Long-Form Video Generation Platform (Wan2.1 / Diffusers / FFmpeg)",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers to Guarantee Pure JSON Responses (Prevent "Unexpected token 'I', Internal Server Error...")
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Validation Error", "status_code": 422}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc) if str(exc) else "An unexpected internal server error occurred.",
            "message": "Internal Server Error",
            "status_code": 500
        }
    )


# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Mount local storage static files for video and thumbnail playback
app.mount("/api/v1/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")

# Mount Web Application Static Files
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main Web UI."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }
