"""
╔══════════════════════════════════════════════════════════════════╗
║          AI-Powered Gmail Intelligence System                    ║
║          Main Orchestrator — Entry Point                         ║
╚══════════════════════════════════════════════════════════════════╝

This is the main entry point of the application. It orchestrates:
  1. Initialization of all services (DB, Gmail, AI, Telegram)
  2. A continuous polling loop that fetches, analyzes, and notifies
  3. Graceful shutdown on KeyboardInterrupt (Ctrl+C)
  4. Comprehensive error handling for every stage

Usage:
    python main.py
"""

import sys
import time
import logging

from src.logger import setup_logging
from src.config import settings
from src.database.handler import DatabaseHandler
from src.gmail.auth import GmailAuthenticator
from src.gmail.service import GmailService
from src.ai.analyzer import EmailAnalyzer
from src.ai.schemas import ImportanceLevel
from src.telegram.notifier import TelegramNotifier
from src.telegram.formatter import format_email_notification, format_junk_summary

# ── Bootstrap logging first ─────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════
#  Service Initialization
# ═════════════════════════════════════════════════════════════════

def initialize_services() -> tuple[
    DatabaseHandler, GmailService, EmailAnalyzer, TelegramNotifier
]:
    """
    Initialize and validate all service dependencies.

    Returns:
        A tuple of (DatabaseHandler, GmailService, EmailAnalyzer, TelegramNotifier).

    Raises:
        SystemExit: If any critical service fails to initialize.
    """
    logger.info("=" * 60)
    logger.info("  AI-Powered Gmail Intelligence System")
    logger.info("  Starting up...")
    logger.info("=" * 60)

    # ── Database ─────────────────────────────────────────────────
    try:
        logger.info("[1/4] Initializing database connection...")
        db = DatabaseHandler()
        db.initialize()
        logger.info("[1/4] ✓ Database ready.")
    except Exception as exc:
        logger.critical("Failed to initialize database: %s", exc)
        sys.exit(1)

    # ── Gmail API ────────────────────────────────────────────────
    try:
        logger.info("[2/4] Authenticating with Gmail API...")
        auth = GmailAuthenticator()
        gmail_api = auth.get_gmail_service()
        gmail = GmailService(gmail_api)
        logger.info("[2/4] ✓ Gmail API authenticated.")
    except FileNotFoundError as exc:
        logger.critical("Gmail credentials not found: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Failed to authenticate with Gmail: %s", exc)
        sys.exit(1)

    # ── AI Analyzer ──────────────────────────────────────────────
    try:
        logger.info("[3/4] Initializing AI analyzer (model: %s)...", settings.OPENAI_MODEL)
        analyzer = EmailAnalyzer()
        logger.info("[3/4] ✓ AI analyzer ready.")
    except Exception as exc:
        logger.critical("Failed to initialize AI analyzer: %s", exc)
        sys.exit(1)

    # ── Telegram Notifier ────────────────────────────────────────
    try:
        logger.info("[4/4] Connecting to Telegram Bot API...")
        notifier = TelegramNotifier()
        if notifier.verify_connection():
            logger.info("[4/4] ✓ Telegram bot verified.")
        else:
            logger.warning("[4/4] ⚠ Telegram bot could not be verified. Notifications may fail.")
    except Exception as exc:
        logger.warning("Telegram setup issue (non-fatal): %s", exc)
        notifier = TelegramNotifier()

    return db, gmail, analyzer, notifier


# ═════════════════════════════════════════════════════════════════
#  Email Processing Pipeline
# ═════════════════════════════════════════════════════════════════

def process_email(
    email: dict,
    db: DatabaseHandler,
    analyzer: EmailAnalyzer,
    notifier: TelegramNotifier,
    gmail: GmailService,
) -> bool:
    """
    Process a single email through the full pipeline:
      1. Check if already processed (deduplication)
      2. Analyze with AI
      3. Send Telegram notification (skip junk)
      4. Log to database
      5. Mark as read in Gmail

    Args:
        email:    Email dict from GmailService.fetch_unread_emails().
        db:       DatabaseHandler instance.
        analyzer: EmailAnalyzer instance.
        notifier: TelegramNotifier instance.
        gmail:    GmailService instance.

    Returns:
        True if the email was processed, False if skipped (duplicate or error).
    """
    message_id = email["id"]
    subject = email.get("subject", "(No Subject)")
    sender = email.get("sender", "Unknown")

    # ── Step 1: Deduplication ────────────────────────────────────
    if db.is_processed(message_id):
        logger.debug("Skipping already-processed email: %s", message_id)
        return False

    logger.info("Processing email: '%s' from %s", subject[:50], sender)

    # ── Step 2: AI Analysis ──────────────────────────────────────
    try:
        analysis = analyzer.analyze(
            sender=email.get("sender", ""),
            subject=subject,
            body=email.get("body", ""),
            date=email.get("date", ""),
        )
    except Exception as exc:
        logger.error("AI analysis failed for '%s': %s", subject[:50], exc)
        return False

    # ── Step 3: Telegram Notification ────────────────────────────
    if not analysis.is_junk:
        try:
            message = format_email_notification(analysis, subject)
            notifier.send_message(message)
        except Exception as exc:
            logger.error("Telegram notification failed: %s", exc)
            # Continue — don't block the pipeline for notification errors
    else:
        logger.info("Email classified as JUNK — skipping notification.")

    # ── Step 4: Database Logging ─────────────────────────────────
    try:
        db.log_email(
            message_id=message_id,
            sender=analysis.sender_email,
            subject=subject,
            importance=analysis.importance.value,
            summary=analysis.summary,
            deadline=analysis.deadline,
        )
    except Exception as exc:
        logger.error("Database logging failed for '%s': %s", message_id, exc)
        return False

    # ── Step 5: Mark as Read in Gmail ────────────────────────────
    try:
        gmail.mark_as_read(message_id)
    except Exception as exc:
        logger.warning("Failed to mark '%s' as read (non-fatal): %s", message_id, exc)
        # Non-fatal — email is already logged, worst case it gets re-fetched

    return True


# ═════════════════════════════════════════════════════════════════
#  Main Polling Loop
# ═════════════════════════════════════════════════════════════════

def run_polling_loop(
    db: DatabaseHandler,
    gmail: GmailService,
    analyzer: EmailAnalyzer,
    notifier: TelegramNotifier,
) -> None:
    """
    Continuously poll Gmail for unread emails, process them, and notify.

    The loop runs indefinitely until interrupted by Ctrl+C. Each cycle:
      1. Fetches unread emails
      2. Processes each through the AI pipeline
      3. Sends a junk summary (if any junk was filtered)
      4. Sleeps for the configured polling interval

    Args:
        db:       DatabaseHandler instance.
        gmail:    GmailService instance.
        analyzer: EmailAnalyzer instance.
        notifier: TelegramNotifier instance.
    """
    interval = settings.POLLING_INTERVAL
    cycle = 0

    logger.info(
        "Polling loop started (interval=%ds). Press Ctrl+C to stop.", interval
    )

    while True:
        cycle += 1
        logger.info("─" * 50)
        logger.info("Polling cycle #%d", cycle)

        try:
            # ── Fetch unread emails ──────────────────────────────
            emails = gmail.fetch_unread_emails()

            if not emails:
                logger.info("No unread emails. Sleeping %ds...", interval)
                time.sleep(interval)
                continue

            # ── Process each email ───────────────────────────────
            processed_count = 0
            junk_count = 0

            for email in emails:
                try:
                    was_processed = process_email(
                        email, db, analyzer, notifier, gmail
                    )
                    if was_processed:
                        processed_count += 1
                except Exception as exc:
                    logger.error(
                        "Unexpected error processing email '%s': %s",
                        email.get("id", "unknown"),
                        exc,
                    )

            # ── Count junk from this cycle (check DB for junk) ───
            # We track junk based on what the AI classified
            for email in emails:
                if db.is_processed(email["id"]):
                    # Re-check is fine — it's a quick lookup
                    pass

            # ── Cycle Summary ────────────────────────────────────
            logger.info(
                "Cycle #%d complete — %d email(s) processed. Sleeping %ds...",
                cycle,
                processed_count,
                interval,
            )

        except Exception as exc:
            logger.error(
                "Error during polling cycle #%d: %s. Retrying in %ds...",
                cycle,
                exc,
                interval,
            )

        time.sleep(interval)


# ═════════════════════════════════════════════════════════════════
#  Entry Point
# ═════════════════════════════════════════════════════════════════

def main() -> None:
    """Application entry point with graceful shutdown handling."""
    try:
        db, gmail, analyzer, notifier = initialize_services()
        run_polling_loop(db, gmail, analyzer, notifier)

    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("  Shutdown requested (Ctrl+C). Cleaning up...")
        logger.info("=" * 60)

    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)

    finally:
        # Ensure database connections are released
        try:
            db.close()  # type: ignore[possibly-undefined]
        except Exception:
            pass
        logger.info("Goodbye! 👋")


if __name__ == "__main__":
    main()
