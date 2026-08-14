"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Prefer repo-root .env when running uvicorn from backend/
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
_LOCAL_ENV = Path(__file__).resolve().parents[1] / ".env"
_ENV_FILES = tuple(
    str(path) for path in (_ROOT_ENV, _LOCAL_ENV, Path(".env")) if path.is_file()
) or (".env",)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = "http://localhost:11434"
    # Tool-calling chat model required (llama3.2 works locally; coder models preferred when they support tools)
    ollama_model: str = "llama3.2"
    database_url: str = "sqlite:///./data/ecommerce.db"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Safety / agent defaults
    sql_row_limit: int = 100
    sql_timeout_seconds: float = 10.0
    agent_recursion_limit: int = 25
    sql_max_attempts: int = 2

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlite_path(self) -> Path:
        """Filesystem path for the sample SQLite database."""
        url = self.database_url
        if url.startswith("sqlite:///"):
            raw = url.removeprefix("sqlite:///")
        elif url.startswith("sqlite://"):
            raw = url.removeprefix("sqlite://")
        else:
            raw = url

        path = Path(raw)
        if not path.is_absolute():
            path = _BACKEND_ROOT / path
        return path.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
