"""
Database Handler
=================
Provides a clean interface for all database operations:
  - Initializing the schema (auto-create tables)
  - Checking whether an email has already been processed
  - Logging a newly processed email

Usage:
    from src.database.handler import DatabaseHandler
    db = DatabaseHandler()
    db.initialize()
"""

import logging
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from src.config import settings
from src.database.models import Base, ProcessedEmail

logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Manages the PostgreSQL connection and all persistence operations."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        """
        Initialize the database engine and session factory.

        Args:
            database_url: Override the default connection URL from settings.
                          Useful for testing with a different database.
        """
        url = database_url or settings.database_url
        self._engine = create_engine(
            url,
            pool_pre_ping=True,      # Verify connections before checkout
            pool_size=5,              # Connection pool size
            max_overflow=10,          # Extra connections beyond pool_size
            echo=False,               # Set True for SQL debug logging
        )
        self._SessionFactory = sessionmaker(bind=self._engine)
        logger.info("Database engine created for host: %s", settings.DB_HOST)

    # ── Schema Management ────────────────────────────────────────

    def initialize(self) -> None:
        """
        Create all tables defined in the ORM models if they don't exist.
        Safe to call multiple times — SQLAlchemy uses IF NOT EXISTS internally.
        """
        Base.metadata.create_all(self._engine)
        logger.info("Database schema initialized (tables created if not present).")

    # ── Query Operations ─────────────────────────────────────────

    def is_processed(self, message_id: str) -> bool:
        """
        Check whether an email with the given Gmail message_id
        has already been processed and logged.

        Args:
            message_id: The Gmail-assigned unique message identifier.

        Returns:
            True if the message_id exists in the database, False otherwise.
        """
        with self._SessionFactory() as session:
            stmt = select(ProcessedEmail.id).where(
                ProcessedEmail.message_id == message_id
            )
            result = session.execute(stmt).scalar_one_or_none()
            return result is not None

    # ── Write Operations ─────────────────────────────────────────

    def log_email(
        self,
        message_id: str,
        sender: str,
        subject: str,
        importance: str = "UNKNOWN",
        summary: Optional[str] = None,
        deadline: Optional[str] = None,
    ) -> ProcessedEmail:
        """
        Insert a processed email record into the database.

        Args:
            message_id: Gmail-assigned unique message identifier.
            sender:     Sender email address (From header).
            subject:    Email subject line.
            importance: AI-classified importance level.
            summary:    AI-generated summary of the email.
            deadline:   Extracted deadline string (if any).

        Returns:
            The newly created ProcessedEmail ORM instance.

        Raises:
            sqlalchemy.exc.IntegrityError: If the message_id already exists
                (unique constraint violation).
        """
        session: Session
        with self._SessionFactory() as session:
            record = ProcessedEmail(
                message_id=message_id,
                sender=sender,
                subject=subject,
                importance=importance,
                summary=summary,
                deadline=deadline,
            )
            session.add(record)
            session.commit()
            session.refresh(record)

            logger.info(
                "Logged email [%s] | From: %s | Importance: %s",
                message_id,
                sender,
                importance,
            )
            return record

    # ── Utility ──────────────────────────────────────────────────

    def close(self) -> None:
        """Dispose of the connection pool and release all resources."""
        self._engine.dispose()
        logger.info("Database connection pool disposed.")
