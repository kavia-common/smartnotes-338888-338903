import os
from dataclasses import dataclass
from typing import List
from urllib.parse import quote


@dataclass(frozen=True)
class Settings:
    """
    Application settings loaded from environment variables.

    Database env vars (provided by the database container):
      - POSTGRES_URL: PostgreSQL connection URL (commonly: postgresql://user:pass@host:port/db)
      - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT: discrete connection parts

    Backend env vars (to be set in notes_backend .env by orchestrator):
      - CORS_ALLOW_ORIGINS: comma-separated list of allowed origins for the frontend
        (e.g. http://localhost:3000,https://your-frontend-domain)
    """

    postgres_url: str
    cors_allow_origins: List[str]


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_postgres_url_from_parts() -> str:
    """
    Build a postgres URL from discrete env vars.

    We intentionally do not assume a host env var name, because it may be embedded
    in POSTGRES_URL by the orchestrator. If only discrete vars are present, we
    fall back to localhost.
    """
    user = os.getenv("POSTGRES_USER", "").strip()
    password = os.getenv("POSTGRES_PASSWORD", "").strip()
    db = os.getenv("POSTGRES_DB", "").strip()
    port = os.getenv("POSTGRES_PORT", "").strip()

    if not (user and password and db and port):
        return ""

    # URL-encode credentials to be safe for special characters
    user_enc = quote(user, safe="")
    pass_enc = quote(password, safe="")

    # Host is not provided in the db_env_vars list; default to localhost.
    return f"postgresql://{user_enc}:{pass_enc}@localhost:{port}/{db}"


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load and validate settings from environment variables."""
    postgres_url = os.getenv("POSTGRES_URL", "").strip()
    if not postgres_url:
        postgres_url = _build_postgres_url_from_parts()

    if not postgres_url:
        # Note: don't hardcode sensitive defaults. Orchestrator will set this in .env.
        raise RuntimeError(
            "Missing database connection configuration. Set POSTGRES_URL, "
            "or set POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT."
        )

    # Ensure async SQLAlchemy can connect with psycopg driver.
    # We accept:
    #   - postgresql+psycopg://...
    #   - postgresql://...
    # and normalize postgresql:// -> postgresql+psycopg://
    if postgres_url.startswith("postgresql://"):
        postgres_url = postgres_url.replace("postgresql://", "postgresql+psycopg://", 1)

    cors_allow_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    cors_allow_origins = _split_csv(cors_allow_origins_raw) if cors_allow_origins_raw else ["http://localhost:3000"]

    return Settings(
        postgres_url=postgres_url,
        cors_allow_origins=cors_allow_origins,
    )
