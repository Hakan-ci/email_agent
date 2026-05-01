"""
SQLAlchemy ORM Models
======================
Defines the database schema for the AI-Powered Gmail Intelligence System.
Tables are auto-created on application startup via `Base.metadata.create_all()`.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Index,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ProcessedEmail(Base):
    """
    Tracks every email that has been fetched, analyzed, and notified.

    The `message_id` column stores the Gmail-assigned unique identifier,
    enabling deduplication across polling cycles so no email is processed twice.
    """

    __tablename__ = "processed_emails"

    # ── Primary Key ──────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Gmail Metadata ───────────────────────────────────────────
    message_id = Column(
        String(255),
        unique=True,
        nullable=False,
        comment="Gmail-assigned unique message identifier",
    )
    sender = Column(
        String(512),
        nullable=False,
        comment="Sender email address (From header)",
    )
    subject = Column(
        Text,
        nullable=False,
        default="(No Subject)",
        comment="Email subject line",
    )

    # ── AI-Extracted Fields ──────────────────────────────────────
    importance = Column(
        String(50),
        nullable=False,
        default="UNKNOWN",
        comment="AI-classified importance: CRITICAL, HIGH, MEDIUM, LOW, JUNK",
    )
    summary = Column(
        Text,
        nullable=True,
        comment="AI-generated concise summary of the email content",
    )
    deadline = Column(
        String(255),
        nullable=True,
        comment="Extracted deadline or due date (if any)",
    )

    # ── Timestamps ───────────────────────────────────────────────
    processed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="UTC timestamp when the email was processed",
    )

    # ── Indexes ──────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_processed_emails_message_id", "message_id"),
        Index("ix_processed_emails_processed_at", "processed_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessedEmail(id={self.id}, message_id='{self.message_id}', "
            f"importance='{self.importance}', subject='{self.subject[:40]}...')>"
        )
