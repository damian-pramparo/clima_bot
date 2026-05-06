from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(  
        validation_alias="DATABASE_URL",
    )
    app_env: str = Field(validation_alias="APP_ENV")
    alert_evaluation_interval_seconds: int = Field(
        ge=5,
        validation_alias="ALERT_EVALUATION_INTERVAL_SECONDS",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Load and cache application settings from the environment."""
    return Settings()


settings = get_settings()
