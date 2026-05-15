from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SENTINEL"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sentinel:sentinel_secret@localhost:5432/sentinel"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-64-random-bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API Keys (all optional)
    ALIENVAULT_OTX_KEY: str = ""
    GREYNOISE_API_KEY: str = ""
    SHODAN_API_KEY: str = ""
    IPINFO_TOKEN: str = ""
    HUNTER_IO_KEY: str = ""
    NEWSAPI_KEY: str = ""
    URLHAUS_API_KEY: str = ""
    VIRUSTOTAL_API_KEY: str = ""
    ABUSEIPDB_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENCAGE_API_KEY: str = ""
    HAVEIBEENPWNED_KEY: str = ""
    SECURITYTRAILS_KEY: str = ""
    CENSYS_API_ID: str = ""
    CENSYS_API_SECRET: str = ""
    INTELX_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_API_ID: str = ""
    TELEGRAM_API_HASH: str = ""

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "sentinel@yourdomain.com"

    # Reports
    REPORTS_DIR: str = "/app/reports"

    # Data retention
    DATA_RETENTION_DAYS: int = 90

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
