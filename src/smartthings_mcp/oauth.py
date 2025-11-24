"""
OAuth token management for SmartThings MCP server.

Handles token storage, validation, and automatic refresh for SmartThings OAuth 2.0 flow.
"""

import base64
import json
import logging
import os
import random
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    """OAuth token data model."""

    access_token: str = Field(description="OAuth access token")
    refresh_token: str = Field(description="OAuth refresh token for obtaining new access tokens")
    expires_at: str = Field(description="ISO format datetime when token expires")
    obtained_at: str = Field(description="ISO format datetime when token was obtained")
    token_type: str = Field(default="Bearer", description="Token type (always Bearer)")
    scope: Optional[str] = Field(default=None, description="OAuth scopes granted")


@dataclass
class OAuthConfig:
    """OAuth configuration for SmartThings."""

    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8080/callback"
    token_file_path: str = "~/.config/smartthings-mcp/tokens.json"


class TokenManager:
    """Manages OAuth tokens with automatic refresh and secure storage."""

    SMARTTHINGS_TOKEN_URL = "https://api.smartthings.com/oauth/token"
    TOKEN_EXPIRY_BUFFER = timedelta(minutes=5)  # Refresh 5 minutes before expiry

    def __init__(self, config: OAuthConfig):
        """
        Initialize token manager with OAuth configuration.

        Args:
            config: OAuth configuration containing client credentials and paths
        """
        self.config = config
        self.token_file_path = Path(os.path.expanduser(config.token_file_path))
        self._refresh_lock = threading.Lock()
        self._cached_token_data: Optional[TokenData] = None

    def load_tokens(self) -> Optional[TokenData]:
        """
        Load tokens from JSON file.

        Returns:
            TokenData if file exists and is valid, None otherwise
        """
        if not self.token_file_path.exists():
            logger.debug(f"Token file does not exist: {self.token_file_path}")
            return None

        try:
            with open(self.token_file_path, "r") as f:
                data = json.load(f)

            token_data = TokenData(**data)
            self._cached_token_data = token_data
            logger.debug("Successfully loaded tokens from file")
            return token_data

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Token file corrupted, deleting: {e}")
            # Delete corrupted token file
            try:
                self.token_file_path.unlink()
                logger.info("Corrupted token file deleted. Please run: python -m smartthings_mcp.oauth_setup")
            except Exception as del_e:
                logger.error(f"Failed to delete corrupted token file: {del_e}")
            return None
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            return None

    def save_tokens(self, token_data: TokenData) -> None:
        """
        Save tokens to JSON file with atomic write operation.

        Uses temp file + rename for atomic writes and sets file permissions to 600.

        Args:
            token_data: Token data to save
        """
        # Ensure parent directory exists
        self.token_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize token data
        token_dict = token_data.model_dump()

        # Write to temp file first for atomic operation
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.token_file_path.parent,
            prefix=".tokens_",
            suffix=".tmp"
        )

        try:
            # Set permissions to 600 (owner read/write only)
            os.chmod(temp_path, 0o600)

            # Write JSON to temp file
            with os.fdopen(temp_fd, "w") as f:
                json.dump(token_dict, f, indent=2)

            # Atomic rename
            os.replace(temp_path, self.token_file_path)

            # Ensure final file has correct permissions
            os.chmod(self.token_file_path, 0o600)

            self._cached_token_data = token_data
            logger.debug("Successfully saved tokens to file")

        except Exception as e:
            # Clean up temp file if it still exists
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            logger.error(f"Failed to save tokens: {e}")
            raise

    def has_valid_tokens(self) -> bool:
        """Check if valid tokens exist."""
        tokens = self.load_tokens()
        return tokens is not None and self.is_token_valid()

    def is_token_valid(self) -> bool:
        """
        Check if current token is valid with expiry buffer.

        Returns:
            True if token exists and is valid, False otherwise
        """
        token_data = self._cached_token_data or self.load_tokens()

        if not token_data:
            return False

        try:
            # Parse expiry time
            expires_at = datetime.fromisoformat(token_data.expires_at.replace("Z", "+00:00"))

            # Get current time with timezone awareness
            now = datetime.now(timezone.utc)

            # Check if token expires after (now + buffer)
            return expires_at > (now + self.TOKEN_EXPIRY_BUFFER)

        except Exception as e:
            logger.error(f"Error checking token validity: {e}")
            return False

    def refresh_access_token(self) -> TokenData:
        """
        Refresh access token using refresh token with comprehensive retry logic.

        Implements exponential backoff for transient network errors and server errors.
        Will not retry on authentication failures (400/401/403).

        Returns:
            New TokenData with refreshed tokens

        Raises:
            Exception: If refresh fails or no refresh token available
        """
        # Load current tokens
        current_tokens = self._cached_token_data or self.load_tokens()

        if not current_tokens:
            raise Exception("No tokens available to refresh. Please run: python -m smartthings_mcp.oauth_setup")

        if not current_tokens.refresh_token:
            raise Exception("No refresh token available. Please run: python -m smartthings_mcp.oauth_setup")

        # SmartThings requires Basic Auth (client_id:client_secret in Authorization header)
        auth_string = f"{self.config.client_id}:{self.config.client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()

        # Prepare refresh request (NO client credentials in body)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": current_tokens.refresh_token,
        }

        # Retry with exponential backoff
        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                # Make refresh request with timeout and Basic Auth
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        self.SMARTTHINGS_TOKEN_URL,
                        data=data,
                        headers={
                            "Authorization": f"Basic {auth_b64}",
                            "Content-Type": "application/x-www-form-urlencoded"
                        }
                    )

                # Check status code
                if response.status_code in [200, 201]:
                    # Success - parse and save tokens
                    token_response = response.json()

                    # Calculate expiry time
                    now = datetime.now(timezone.utc)
                    expires_in = token_response.get("expires_in", 3600)  # Default to 1 hour
                    expires_at = now + timedelta(seconds=expires_in)

                    # Create new token data
                    new_token_data = TokenData(
                        access_token=token_response["access_token"],
                        refresh_token=token_response.get("refresh_token", current_tokens.refresh_token),
                        expires_at=expires_at.isoformat(),
                        obtained_at=now.isoformat(),
                        token_type=token_response.get("token_type", "Bearer"),
                        scope=token_response.get("scope", current_tokens.scope)
                    )

                    # Save new tokens
                    self.save_tokens(new_token_data)

                    logger.info("Successfully refreshed access token")
                    return new_token_data

                elif response.status_code == 400:
                    # Check for specific OAuth errors
                    try:
                        error_data = response.json()
                        if error_data.get("error") == "invalid_grant":
                            logger.error("Refresh token expired or invalid")
                            raise Exception("Refresh token expired. Please run: python -m smartthings_mcp.oauth_setup")
                        else:
                            error_msg = f"OAuth error: {error_data.get('error', 'unknown')} - {error_data.get('error_description', 'No description')}"
                            logger.error(error_msg)
                            raise Exception(error_msg)
                    except json.JSONDecodeError:
                        error_msg = f"Bad request during token refresh: {response.status_code}"
                        logger.error(error_msg)
                        raise Exception(error_msg)

                elif response.status_code in [401, 403]:
                    # Authentication/authorization failure - don't retry
                    error_msg = f"Authentication failed during token refresh: {response.status_code}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                elif response.status_code == 429:
                    # Rate limited - retry with backoff
                    last_error = "Token refresh rate limited"
                    logger.warning(f"Token refresh attempt {attempt + 1} rate limited")

                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    last_error = f"Server error during token refresh: {response.status_code}"
                    logger.warning(f"Token refresh attempt {attempt + 1} failed with server error: {response.status_code}")

                else:
                    # Unexpected status code - retry
                    last_error = f"Unexpected response during token refresh: {response.status_code}"
                    logger.warning(f"Token refresh attempt {attempt + 1} failed with status: {response.status_code}")

            except (httpx.NetworkError, httpx.TimeoutException) as e:
                # Network error - retry with backoff
                last_error = f"Network error during token refresh: {e}"
                logger.warning(f"Token refresh attempt {attempt + 1} failed with network error: {type(e).__name__}")

            except httpx.RequestError as e:
                # Other request error - retry with backoff
                last_error = f"Request error during token refresh: {e}"
                logger.warning(f"Token refresh attempt {attempt + 1} failed with request error: {type(e).__name__}")

            except KeyError as e:
                # Invalid response format - don't retry
                error_msg = f"Invalid token response format: missing {e}"
                logger.error(error_msg)
                raise Exception(error_msg)

            except json.JSONDecodeError as e:
                # JSON parsing error - don't retry
                error_msg = f"Invalid JSON in token response: {e}"
                logger.error(error_msg)
                raise Exception(error_msg)

            except Exception as e:
                # Unexpected error - don't retry
                error_msg = f"Unexpected error during token refresh: {e}"
                logger.error(error_msg)
                raise

            # If we get here, we should retry (if attempts remain)
            if attempt < max_attempts - 1:
                # Calculate backoff with jitter
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Retrying token refresh in {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
            else:
                # All retries exhausted
                error_msg = f"Token refresh failed after {max_attempts} attempts. Last error: {last_error}"
                logger.error(error_msg)
                raise Exception(error_msg)

    def get_valid_token(self) -> str:
        """
        Get valid access token, automatically refreshing if expired.

        Thread-safe implementation ensures only one refresh happens at a time.

        Returns:
            Valid access token string

        Raises:
            Exception: If unable to obtain valid token
        """
        # First check without lock for performance
        if self.is_token_valid():
            token_data = self._cached_token_data or self.load_tokens()
            if token_data:
                return token_data.access_token

        # Need to refresh - acquire lock
        with self._refresh_lock:
            # Double-check after acquiring lock (another thread might have refreshed)
            if self.is_token_valid():
                token_data = self._cached_token_data or self.load_tokens()
                if token_data:
                    return token_data.access_token

            # Token expired or invalid, refresh it
            logger.info("Token expired or invalid, refreshing...")

            try:
                new_token_data = self.refresh_access_token()
                return new_token_data.access_token
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                raise Exception(f"Unable to obtain valid access token: {e}")