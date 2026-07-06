from fastapi import APIRouter
from .routes import forecast_router

api_router = APIRouter()

api_router.include_router(forecast_router, prefix="/forecast", tags=["forecast"])

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ForecastIQ API"}
