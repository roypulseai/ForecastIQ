"""FastAPI application entry point."""
from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .api.public import build_public_router
from .core.config import settings
from .middleware.auth import require_jwt

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

def get_request_id() -> str:
    return _request_id.get()

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id()
        return True

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s [%(request_id)s]: %(message)s",
)
logging.getLogger().addFilter(RequestIdFilter())
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings.ensure_dirs()
    app = FastAPI(
        title=f"{settings.PROJECT_NAME} API",
        version=settings.VERSION,
        description=(
            f"# {settings.PROJECT_NAME}\n\n"
            "Advanced time series forecasting API with multiple ML models, "
            "external factor integration, ensemble support, and a built-in "
            "model registry for the data-science train/save/load workflow.\n\n"
            "## Two surfaces\n\n"
            "* **Internal UI** (`/api/v1/*`): used by the React frontend. "
            "No API key required when the browser is the client.\n"
            "* **Public API** (`/v1/*`): versioned, API-key authenticated, "
            "rate-limited. Use this from notebooks, scripts, or other tools.\n\n"
            "## Authentication (public API)\n\n"
            "Pass an API key in one of these headers:\n\n"
            "```\nAuthorization: Bearer fiq_live_xxxxxx_secretsecret...\n"
            "X-API-Key: fiq_live_xxxxxx_secretsecret...\n```\n\n"
            "Generate a key in the UI at **Settings → API keys** or via "
            "`POST /api/v1/api-keys`.\n\n"
            "## Rate limits\n\n"
            "Per-key, per-minute, fixed window. See `GET /api/v1/api-keys/tiers`.\n\n"
            "## Pagination\n\n"
            "List endpoints accept `limit` (1-200, default 50) and `offset` (≥0).\n"
            "The response includes `total`, `limit`, `offset`.\n\n"
            "## Async forecasts\n\n"
            "Long forecasts support async execution. POST `/v1/forecast?async=true` "
            "returns a `job_id`; poll `GET /v1/jobs/{job_id}` for progress, "
            "or `GET /v1/jobs/{job_id}/result` to block until completion.\n"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "upload", "description": "File upload, list, delete, and row fetch."},
            {"name": "analyze", "description": "Sales-data analysis and model recommendations."},
            {"name": "forecast", "description": "Train new models and produce a forecast."},
            {"name": "models", "description": "Trained model registry: train, save, upload, download, forecast with."},
            {"name": "api-keys", "description": "Manage API keys for the public /v1 API."},
            {"name": "Public API", "description": "Versioned, API-key-authenticated surface at /v1/*."},
        ],
    )

    # CORS — explicit origins only (wildcard incompatible with credentials)
    allow_credentials = True
    cors_origins = list(settings.BACKEND_CORS_ORIGINS)
    if "*" in cors_origins and allow_credentials:
        cors_origins = [o for o in cors_origins if o != "*"]
        logger.warning("'*' removed from BACKEND_CORS_ORIGINS because allow_credentials=True")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.middleware.request_id import RequestIdMiddleware
    app.add_middleware(RequestIdMiddleware)

    # Serve templates + outputs
    try:
        app.mount("/templates", StaticFiles(directory=settings.TEMPLATE_DIR), name="templates")
    except Exception as e:
        logger.warning("Could not mount /templates: %s", e)
    try:
        app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")
    except Exception as e:
        logger.warning("Could not mount /outputs: %s", e)

    app.include_router(
        api_router,
        prefix=settings.API_V1_STR,
    )

    from app.api.routes.auth import router as auth_router
    app.include_router(auth_router)

    # Public, versioned, API-key-authenticated API at /v1/*
    public_router = build_public_router()
    app.include_router(
        public_router,
        prefix="/v1",
        responses={
            401: {"description": "Missing or invalid API key"},
            429: {"description": "Rate limit exceeded"},
        },
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        logger.exception("Unhandled exception")
        content: dict = {"detail": "Internal server error"}
        if settings.DEBUG:
            content["error"] = str(exc)
        return JSONResponse(
            status_code=500,
            content=content,
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
