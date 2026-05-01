"""
Gmail OAuth 2.0 Authentication
================================
Handles the full OAuth 2.0 lifecycle for the Gmail API:
  - Loading cached tokens from disk (token.json)
  - Refreshing expired tokens automatically
  - Running the interactive consent flow on first use
  - Persisting new tokens for subsequent runs

Usage:
    from src.gmail.auth import GmailAuthenticator
    service = GmailAuthenticator.get_gmail_service()
"""

import logging
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from src.config import settings

logger = logging.getLogger(__name__)

# Gmail API scopes — modify & readonly for reading + marking emails as read
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailAuthenticator:
    """
    Manages Gmail OAuth 2.0 credentials and builds the API service client.

    The authentication state is persisted to a token file so that
    subsequent runs skip the interactive browser-based consent flow.
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
    ) -> None:
        """
        Args:
            credentials_path: Path to the OAuth client secrets JSON
                              downloaded from Google Cloud Console.
            token_path:       Path where the authenticated token is cached.
        """
        self._credentials_path = Path(credentials_path or settings.GMAIL_CREDENTIALS_PATH)
        self._token_path = Path(token_path or settings.GMAIL_TOKEN_PATH)
        self._credentials: Optional[Credentials] = None

    # ── Public API ───────────────────────────────────────────────

    def authenticate(self) -> Credentials:
        """
        Obtain valid Gmail API credentials through one of three paths:
          1. Load a cached token from disk (fast path).
          2. Refresh an expired-but-refreshable token.
          3. Run the full interactive OAuth consent flow.

        Returns:
            A valid google.oauth2.credentials.Credentials instance.

        Raises:
            FileNotFoundError: If credentials.json is missing and no
                               cached token exists.
        """
        creds = self._load_cached_token()

        if creds and creds.valid:
            logger.info("Loaded valid cached token from '%s'.", self._token_path)
            self._credentials = creds
            return creds

        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired — refreshing automatically.")
            creds.refresh(Request())
            self._save_token(creds)
            self._credentials = creds
            return creds

        # No valid token — run the interactive consent flow
        logger.info("No valid token found — launching OAuth consent flow.")
        creds = self._run_consent_flow()
        self._save_token(creds)
        self._credentials = creds
        return creds

    def get_gmail_service(self) -> Resource:
        """
        Build and return an authorized Gmail API service client.

        Returns:
            A googleapiclient.discovery.Resource for the Gmail API v1.
        """
        creds = self.authenticate()
        service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail API service client built successfully.")
        return service

    # ── Private Helpers ──────────────────────────────────────────

    def _load_cached_token(self) -> Optional[Credentials]:
        """Load credentials from the cached token file if it exists."""
        if self._token_path.exists():
            try:
                return Credentials.from_authorized_user_file(
                    str(self._token_path), SCOPES
                )
            except Exception as exc:
                logger.warning(
                    "Failed to load cached token ('%s'): %s", self._token_path, exc
                )
        return None

    def _run_consent_flow(self) -> Credentials:
        """
        Execute the interactive OAuth 2.0 consent flow.

        Opens a local browser window for the user to authorize Gmail access.
        Requires credentials.json to be present.

        Raises:
            FileNotFoundError: If the credentials file does not exist.
        """
        if not self._credentials_path.exists():
            raise FileNotFoundError(
                f"OAuth credentials file not found at '{self._credentials_path}'. "
                f"Download it from the Google Cloud Console and place it at that path. "
                f"See README.md for detailed setup instructions."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._credentials_path), SCOPES
        )
        creds = flow.run_local_server(port=0)
        logger.info("OAuth consent flow completed successfully.")
        return creds

    def _save_token(self, creds: Credentials) -> None:
        """Persist credentials to the token file for future runs."""
        self._token_path.write_text(creds.to_json())
        logger.info("Token saved to '%s'.", self._token_path)
