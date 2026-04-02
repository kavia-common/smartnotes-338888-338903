import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Settings:
    """
    Application settings loaded from environment variables.

    Env vars (to be set in notes_backend .env by orchestrator):
      - POSTGRES_URL: SQLAlchemy-style database URL (e.g. postgresql+psycopg://user:pass@host:port/db)
      - CORS_ALLOW_ORIGINS: comma-separated list of allowed origins for the frontend (e.g. http://localhost:3000,https://...)
    """

    postgres_url: str
    cors_allow_origins: List[str]


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load and validate settings from environment variables."""
    postgres_url = os.getenv("POSTGRES_URL", "").strip()
    if not postgres_url:
        # Note: don't hardcode sensitive defaults. Orchestrator will set this in .env.
        raise RuntimeError("Missing required environment variable POSTGRES_URL")

    cors_allow_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    cors_allow_origins = _split_csv(cors_allow_origins_raw) if cors_allow_origins_raw else ["*"]

    return Settings(
        postgres_url=postgres_url,
        cors_allow_origins=cors_allow_origins,
    )
