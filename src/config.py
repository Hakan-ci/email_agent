"""
Centralized Configuration Loader
=================================
Loads all environment variables from the .env file and exposes them
as typed attributes on a singleton Settings instance.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


class Settings:
    """Application-wide settings sourced from environment variables."""

    # --- OpenAI ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- Gmail API ---
    GMAIL_CREDENTIALS_PATH: str = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    GMAIL_TOKEN_PATH: str = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    GMAIL_MAX_RESULTS: int = int(os.getenv("GMAIL_MAX_RESULTS", "5"))

    # --- PostgreSQL ---
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "email_agent")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # --- Application ---
    POLLING_INTERVAL: int = int(os.getenv("POLLING_INTERVAL", "60"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def database_url(self) -> str:
        """Construct the PostgreSQL connection URL for SQLAlchemy."""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


# Singleton instance — import this across all modules
settings = Settings()
