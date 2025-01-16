"""Configuration management for the Datadog downloader."""

import os
from functools import lru_cache
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv(dotenv_path=".env")


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    datadog_api_key: str = Field(alias="DATADOG_API_KEY")
    datadog_app_key: str = Field(alias="DATADOG_APP_KEY")
    datadog_site: str = Field(default="datadoghq.com", alias="DATADOG_SITE")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings(
        DATADOG_API_KEY=os.getenv("DATADOG_API_KEY"),
        DATADOG_APP_KEY=os.getenv("DATADOG_APP_KEY"),
        DATADOG_SITE=os.getenv("DATADOG_SITE", "datadoghq.com"),
    )


settings = get_settings()
