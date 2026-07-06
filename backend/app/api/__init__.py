"""API router aggregation."""
from fastapi import APIRouter

from .routes.analyze import router as analyze_router
from .routes.forecast import router as forecast_router
from .routes.upload import router as upload_router

api_router = APIRouter()
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(analyze_router, tags=["analyze"])
api_router.include_router(forecast_router, tags=["forecast"])


@api_router.get("/health")
async def health_check() -> dict:
    from datetime import datetime
    return {
        "status": "healthy",
        "service": "ForecastIQ API",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "components": {
            "storage": "ready",
            "models": "ready",
        },
    }
