"""
Telegram Bot Notifier
======================
Sends formatted messages to a Telegram chat using the Bot API.

Uses the `requests` library for direct HTTP calls to the Telegram
Bot API — lightweight and dependency-free compared to full bot frameworks.

Usage:
    from src.telegram.notifier import TelegramNotifier

    notifier = TelegramNotifier()
    notifier.send_message("Hello from the email agent!")
"""

import logging
from typing import Optional

import requests

from src.config import settings

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
_API_BASE = "https://api.telegram.org/bot{token}"


class TelegramNotifier:
    """
    Sends messages to a Telegram chat via the Bot API.

    Supports plain text and MarkdownV2 formatted messages
    with automatic retry and error reporting.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """
        Args:
            bot_token: Telegram Bot API token from @BotFather.
                       Defaults to TELEGRAM_BOT_TOKEN from settings.
            chat_id:   Target chat/user ID for notifications.
                       Defaults to TELEGRAM_CHAT_ID from settings.
            timeout:   HTTP request timeout in seconds.
        """
        self._token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self._chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self._timeout = timeout
        self._base_url = _API_BASE.format(token=self._token)

        if not self._token:
            logger.warning("Telegram bot token is not configured.")
        if not self._chat_id:
            logger.warning("Telegram chat ID is not configured.")

    # ── Public API ───────────────────────────────────────────────

    def send_message(
        self,
        text: str,
        parse_mode: str = "MarkdownV2",
        disable_preview: bool = True,
    ) -> bool:
        """
        Send a text message to the configured Telegram chat.

        Args:
            text:            The message text (plain or formatted).
            parse_mode:      Telegram parse mode: 'MarkdownV2', 'HTML', or None.
            disable_preview: If True, disables link previews in the message.

        Returns:
            True if the message was sent successfully, False otherwise.
        """
        if not self._token or not self._chat_id:
            logger.error(
                "Cannot send Telegram message: bot_token or chat_id not configured."
            )
            return False

        url = f"{self._base_url}/sendMessage"

        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "disable_web_page_preview": disable_preview,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            response = requests.post(
                url, json=payload, timeout=self._timeout
            )
            data = response.json()

            if response.ok and data.get("ok"):
                logger.info("Telegram message sent successfully.")
                return True

            # API returned an error
            error_desc = data.get("description", "Unknown error")
            error_code = data.get("error_code", "N/A")
            logger.error(
                "Telegram API error [%s]: %s", error_code, error_desc
            )

            # If MarkdownV2 parsing fails, retry as plain text
            if parse_mode == "MarkdownV2" and "parse" in error_desc.lower():
                logger.warning("Retrying message as plain text (no formatting).")
                return self.send_message(
                    text=text, parse_mode="", disable_preview=disable_preview
                )

            return False

        except requests.exceptions.Timeout:
            logger.error("Telegram API request timed out after %ds.", self._timeout)
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Telegram API. Check network.")
            return False
        except Exception as exc:
            logger.error("Unexpected error sending Telegram message: %s", exc)
            return False

    # ── Utility ──────────────────────────────────────────────────

    def verify_connection(self) -> bool:
        """
        Verify the bot token is valid by calling the Telegram `getMe` endpoint.

        Returns:
            True if the bot token is valid and the API is reachable.
        """
        if not self._token:
            logger.error("No bot token configured — cannot verify.")
            return False

        url = f"{self._base_url}/getMe"

        try:
            response = requests.get(url, timeout=self._timeout)
            data = response.json()

            if response.ok and data.get("ok"):
                bot_info = data.get("result", {})
                bot_name = bot_info.get("first_name", "Unknown")
                bot_username = bot_info.get("username", "Unknown")
                logger.info(
                    "Telegram bot verified: %s (@%s)", bot_name, bot_username
                )
                return True

            logger.error("Telegram bot verification failed: %s", data)
            return False

        except Exception as exc:
            logger.error("Failed to verify Telegram bot: %s", exc)
            return False
