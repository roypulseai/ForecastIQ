from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "ForecastIQ"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")
    
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024
    ALLOWED_EXTENSIONS: list = [".csv", ".xlsx", ".xls"]
    
    class Config:
        case_sensitive = True

settings = Settings()
