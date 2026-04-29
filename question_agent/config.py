"""Application configuration via pydantic-settings.

Reads from environment variables and .env file.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- GLM API ---
    glm_api_key: str = ""
    glm_model: str = "glm-5-flash"

    # --- Paths ---
    project_root: Path = Path(__file__).resolve().parent.parent

    # --- API ---
    debug: bool = True
    api_prefix: str = "/api/v1"


settings = Settings()
