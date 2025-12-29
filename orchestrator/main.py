"""
DeepAgent Orchestrator - Main entry point.

FastAPI application with background worker for task processing.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router as api_router
from .config import get_settings
from .core.worker import get_worker
from .db import close_db, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager for startup/shutdown."""
    settings = get_settings()

    # Startup
    logger.info("Starting DeepAgent Orchestrator")

    # Initialize database
    logger.info(f"Connecting to database: {settings.database_url}")
    await init_db(settings.database_url)

    # Start background worker
    worker = get_worker()
    worker_task = asyncio.create_task(worker.start())
    logger.info("Background worker started")

    yield

    # Shutdown
    logger.info("Shutting down DeepAgent Orchestrator")

    # Stop worker
    await worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    # Close database
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DeepAgent Orchestrator",
    description="AI-powered research and document generation service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
        },
    )


# Include API routes
app.include_router(api_router)


# Serve Flutter web app static files
# Look for the app in common locations
_flutter_web_paths = [
    Path(__file__).parent.parent / "app" / "build" / "web",  # Local dev
    Path("/app/deepagent/app/build/web"),  # Container
]

_flutter_web_dir = None
for p in _flutter_web_paths:
    if p.exists() and (p / "index.html").exists():
        _flutter_web_dir = p
        break

if _flutter_web_dir:
    logger.info(f"Serving Flutter web app from: {_flutter_web_dir}")

    # Serve index.html for the root path
    @app.get("/")
    async def serve_flutter_app():
        return FileResponse(_flutter_web_dir / "index.html")

    # Mount static files (but not at root to avoid conflicts with API)
    app.mount("/", StaticFiles(directory=str(_flutter_web_dir), html=True), name="static")
else:
    logger.warning("Flutter web app not found, serving API-only mode")

    # Root endpoint (API-only mode)
    @app.get("/")
    async def root():
        return {
            "name": "DeepAgent Orchestrator",
            "version": "1.0.0",
            "docs": "/docs",
        }


def main():
    """Run the application with uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "orchestrator.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
