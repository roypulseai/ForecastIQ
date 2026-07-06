"""FastAPI application entry point."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .core.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings.ensure_dirs()
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Advanced time series forecasting API with multiple ML models, "
                    "external factor integration, and ensemble support.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — explicit origins only (wildcard incompatible with credentials)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve templates + outputs
    try:
        app.mount("/templates", StaticFiles(directory=settings.TEMPLATE_DIR), name="templates")
    except Exception as e:
        logger.warning("Could not mount /templates: %s", e)
    try:
        app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")
    except Exception as e:
        logger.warning("Could not mount /outputs: %s", e)

    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)},
        )

    @app.get("/")
    async def root() -> dict:
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "api": settings.API_V1_STR,
            "templates": "/templates",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
