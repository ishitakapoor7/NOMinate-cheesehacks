"""Environment-based configuration.

Secrets and connection strings come from environment variables (loaded from a
.env file in development). Nothing sensitive is hardcoded.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_db_url(url: str) -> str:
    """Force the psycopg3 driver. Managed hosts (Render, Heroku) inject
    ``postgres://`` or ``postgresql://`` URLs, which SQLAlchemy maps to the
    psycopg2 dialect we don't install."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]

    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://nominate:nominate@localhost:5432/nominate",
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173"))

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
    SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.getenv(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://nominate:nominate@localhost:5432/nominate_test",
        )
    )


def get_config() -> type[Config]:
    """Pick the config class based on FLASK_ENV."""
    if os.getenv("FLASK_ENV") == "testing":
        return TestConfig
    return Config
