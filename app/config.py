import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = "OCR Service"
    APP_ENV: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Uploads & Limits
    MAX_UPLOAD_SIZE_MB: int = 10

    # OCR & PDF Processing Settings
    OCR_LANGUAGE: str = "vi"
    PDF_RENDER_DPI: int = 200
    PDF_MAX_PAGES: int = 20
    MIN_TEXT_LENGTH_THRESHOLD: int = 20

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
