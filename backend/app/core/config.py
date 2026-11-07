import os
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "LocalPulse AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # MongoDB settings
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "localpulse"

    # Security
    # Loaded strictly from .env (never hardcoded in source code)
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: Optional[str] = None

    # Modular LLM Configuration
    LLM_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini"  # gemini, openai, groq, or custom
    LLM_MODEL: str = "gemini-3.8-flash"  # Active Gemini model ID
    LLM_BASE_URL: Optional[str] = None

    # Sarvam AI Configuration (Multilingual Indic Voice & Speech-to-Text)
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_STT_MODEL: str = "saaras:v4"  # Latest Indic multi-language model

    # Calendarific API Key (Real All-India Festivals & Occasions: https://calendarific.com)
    CALENDARIFIC_API_KEY: Optional[str] = None

    @property
    def cors_origins(self) -> list[str]:
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
        for source in [self.FRONTEND_URL, self.ALLOWED_ORIGINS]:
            if source:
                for item in source.split(","):
                    cleaned = item.strip().rstrip("/")
                    if cleaned and cleaned not in origins:
                        origins.append(cleaned)
        return origins

    model_config = SettingsConfigDict(
        env_file=[".env", "backend/.env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
