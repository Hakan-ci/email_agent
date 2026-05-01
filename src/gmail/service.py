"""
Gmail Service Layer
====================
High-level interface for interacting with the Gmail API:
  - Fetching unread emails with decoded body content
  - Marking messages as read (removing the UNREAD label)

Usage:
    from src.gmail.auth import GmailAuthenticator
    from src.gmail.service import GmailService

    auth = GmailAuthenticator()
    api = auth.get_gmail_service()
    gmail = GmailService(api)

    emails = gmail.fetch_unread_emails(max_results=5)
    gmail.mark_as_read(emails[0]["id"])
"""

import base64
import logging
from typing import Any, Optional

from googleapiclient.discovery import Resource

from src.config import settings

logger = logging.getLogger(__name__)


class GmailService:
    """
    Wraps the Gmail API client to provide clean methods
    for fetching and managing email messages.
    """

    def __init__(self, service: Resource) -> None:
        """
        Args:
            service: An authorized Gmail API Resource from GmailAuthenticator.
        """
        self._service = service
        self._user_id = "me"  # Authenticated user's inbox

    # ── Fetch Emails ─────────────────────────────────────────────

    def fetch_unread_emails(
        self, max_results: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Fetch unread emails from the authenticated user's inbox.

        Args:
            max_results: Maximum number of messages to retrieve.
                         Defaults to GMAIL_MAX_RESULTS from settings.

        Returns:
            A list of dicts, each containing:
              - id:      Gmail message ID
              - sender:  From header value
              - subject: Subject line
              - date:    Date header value
              - body:    Decoded plain-text body (or HTML fallback)
              - snippet: Gmail-provided snippet preview
        """
        limit = max_results or settings.GMAIL_MAX_RESULTS

        # Step 1: List unread message IDs
        response = (
            self._service.users()
            .messages()
            .list(
                userId=self._user_id,
                q="is:unread",
                maxResults=limit,
            )
            .execute()
        )

        message_stubs = response.get("messages", [])

        if not message_stubs:
            logger.info("No unread emails found.")
            return []

        logger.info("Found %d unread email(s). Fetching details...", len(message_stubs))

        # Step 2: Fetch full message details for each ID
        emails = []
        for stub in message_stubs:
            try:
                email_data = self._get_message_detail(stub["id"])
                if email_data:
                    emails.append(email_data)
            except Exception as exc:
                logger.error(
                    "Failed to fetch message '%s': %s", stub["id"], exc
                )

        logger.info("Successfully fetched %d email(s).", len(emails))
        return emails

    # ── Mark as Read ─────────────────────────────────────────────

    def mark_as_read(self, message_id: str) -> None:
        """
        Remove the UNREAD label from a message, marking it as read.

        Args:
            message_id: The Gmail message ID to mark as read.
        """
        try:
            self._service.users().messages().modify(
                userId=self._user_id,
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            logger.info("Marked message '%s' as read.", message_id)
        except Exception as exc:
            logger.error(
                "Failed to mark message '%s' as read: %s", message_id, exc
            )
            raise

    # ── Private Helpers ──────────────────────────────────────────

    def _get_message_detail(self, message_id: str) -> Optional[dict[str, Any]]:
        """
        Fetch full message content and extract key fields.

        Args:
            message_id: The Gmail message ID to retrieve.

        Returns:
            A dict with parsed email fields, or None on failure.
        """
        message = (
            self._service.users()
            .messages()
            .get(
                userId=self._user_id,
                id=message_id,
                format="full",
            )
            .execute()
        )

        headers = {
            h["name"].lower(): h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }

        body = self._extract_body(message.get("payload", {}))

        return {
            "id": message_id,
            "sender": headers.get("from", "Unknown Sender"),
            "subject": headers.get("subject", "(No Subject)"),
            "date": headers.get("date", ""),
            "body": body,
            "snippet": message.get("snippet", ""),
        }

    def _extract_body(self, payload: dict) -> str:
        """
        Recursively extract the email body from the message payload.

        Prefers text/plain over text/html. Handles both simple and
        multipart message structures.

        Args:
            payload: The Gmail message payload dict.

        Returns:
            The decoded body text, or an empty string if not found.
        """
        # Simple (non-multipart) message
        mime_type = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data")

        if body_data and mime_type == "text/plain":
            return self._decode_base64(body_data)

        # Multipart — search parts recursively
        parts = payload.get("parts", [])
        plain_text = ""
        html_text = ""

        for part in parts:
            part_mime = part.get("mimeType", "")
            part_data = part.get("body", {}).get("data")

            if part_data:
                decoded = self._decode_base64(part_data)
                if part_mime == "text/plain":
                    plain_text = decoded
                elif part_mime == "text/html":
                    html_text = decoded

            # Recurse into nested multipart structures
            if part.get("parts"):
                nested = self._extract_body(part)
                if nested:
                    plain_text = plain_text or nested

        # Prefer plain text; fall back to HTML; last resort: top-level data
        if plain_text:
            return plain_text
        if html_text:
            return html_text
        if body_data:
            return self._decode_base64(body_data)

        return ""

    @staticmethod
    def _decode_base64(data: str) -> str:
        """
        Decode a URL-safe base64 encoded string (Gmail's encoding).

        Args:
            data: The base64url-encoded string.

        Returns:
            The decoded UTF-8 text.
        """
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Base64 decode failed: %s", exc)
            return ""
