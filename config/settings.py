import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "ScamShield"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_TOKENS: int = 1000
    
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/scamshield"
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    
    ES_CLOUD_ID: Optional[str] = None
    ES_API_KEY: Optional[str] = None
    ES_URL: str = "http://localhost:9200"
    
    REDIS_URL: str = "redis://localhost:6379"
    
    JWT_SECRET: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 15
    
    RATE_LIMIT_PER_MINUTE: int = 100
    
    RISK_SCORE_BLOCK_THRESHOLD: int = 70
    RISK_SCORE_WARN_THRESHOLD: int = 40
    
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "scamshield"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
