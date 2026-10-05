import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = "OCR Service"
    APP_ENV: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # MySQL Database Settings
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306
    DB_NAME: str = "ocr_db"
    DB_USER: str = "ocr_user"
    DB_PASSWORD: str = "ocr_password_secure_123"

    # Uploads & Limits
    MAX_UPLOAD_SIZE_MB: int = 10

    # OCR & PDF Processing Settings
    OCR_LANGUAGE: str = "vi"
    PDF_RENDER_DPI: int = 200
    MIN_TEXT_LENGTH_THRESHOLD: int = 20

    @property
    def database_url(self) -> str:
        # Nếu DB_HOST rỗng hoặc "sqlite", hỗ trợ fallback SQLite cho test
        if self.DB_HOST.lower() in ("sqlite", ":memory:"):
            return "sqlite:///./test.db"
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
