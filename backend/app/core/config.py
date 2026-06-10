"""Centralized settings for the ADGM Compliance Copilot backend.

Settings are loaded from environment variables and `.env` during local
development. Other layers depend on this module for database, vector store,
cache, and model configuration.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.core.constants import APP_NAME


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = APP_NAME
    app_env: Literal["local", "dev", "test", "staging", "prod"] = "local"
    app_debug: bool = True
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "adgm_db"
    postgres_user: str = "postgres"
    postgres_password: SecretStr = Field(default=SecretStr("postgres"))

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: SecretStr | None = None
    qdrant_https: bool = False

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: SecretStr | None = None

    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def postgres_url(self) -> str:
        """Return a SQLAlchemy-compatible PostgreSQL connection URL."""

        password = self.postgres_password.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Return a Redis connection URL."""

        password = (
            self.redis_password.get_secret_value()
            if self.redis_password is not None
            else None
        )
        auth = f":{password}@" if password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()

