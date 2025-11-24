#!/usr/bin/env python3
"""
OAuth setup flow for SmartThings MCP

This script handles the OAuth authorization flow by:
1. Starting a local HTTP server to receive the callback
2. Opening the browser to the SmartThings authorization page
3. Exchanging the authorization code for tokens
4. Saving the tokens securely
"""

import base64
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Tuple

import httpx

from .oauth import OAuthConfig, TokenData, TokenManager


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback"""

    auth_code: Optional[str] = None
    error_message: Optional[str] = None
    received_callback = threading.Event()
    expected_state: Optional[str] = None  # CSRF protection

    def do_GET(self):
        """Handle GET request for OAuth callback"""
        # Parse the URL and query parameters
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/callback":
            query_params = urllib.parse.parse_qs(parsed_path.query)

            # Validate CSRF state parameter
            received_state = query_params.get("state", [None])[0]
            if received_state != OAuthCallbackHandler.expected_state:
                OAuthCallbackHandler.error_message = (
                    "Invalid state parameter - possible CSRF attack"
                )
                self._send_error_response("Security validation failed")
                OAuthCallbackHandler.received_callback.set()
                return

            # Check for authorization code
            if "code" in query_params:
                OAuthCallbackHandler.auth_code = query_params["code"][0]
                self._send_success_response()
            elif "error" in query_params:
                error = query_params.get("error", ["unknown"])[0]
                error_description = query_params.get("error_description", [""])[0]
                OAuthCallbackHandler.error_message = f"{error}: {error_description}"
                self._send_error_response(OAuthCallbackHandler.error_message)
            else:
                OAuthCallbackHandler.error_message = "No authorization code received"
                self._send_error_response("Invalid callback - no authorization code")

            # Signal that we've received the callback
            OAuthCallbackHandler.received_callback.set()
        else:
            self.send_error(404)

    def _send_success_response(self):
        """Send success HTML response"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SmartThings Authorization Successful</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 400px;
                }
                h1 { color: #2d3436; margin-bottom: 10px; }
                p { color: #636e72; line-height: 1.6; }
                .success { color: #00b894; font-size: 48px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✓</div>
                <h1>Authorization Successful!</h1>
                <p>SmartThings MCP has been successfully authorized.</p>
                <p>You can now close this window and return to your terminal.</p>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_content.encode())

    def _send_error_response(self, error_message: str):
        """Send error HTML response"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SmartThings Authorization Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 400px;
                }}
                h1 {{ color: #2d3436; margin-bottom: 10px; }}
                p {{ color: #636e72; line-height: 1.6; }}
                .error {{ color: #d63031; font-size: 48px; margin-bottom: 20px; }}
                .error-detail {{
                    background: #fee;
                    padding: 10px;
                    border-radius: 5px;
                    margin-top: 15px;
                    font-family: monospace;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">✗</div>
                <h1>Authorization Failed</h1>
                <p>There was a problem authorizing SmartThings MCP.</p>
                <div class="error-detail">{error_message}</div>
                <p>Please return to your terminal and try again.</p>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_content.encode())

    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        pass


def start_callback_server(
    port: int = 8080, timeout: int = 300, expected_state: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Start local HTTP server and wait for OAuth callback

    Args:
        port: Port to listen on
        timeout: Timeout in seconds (default 5 minutes)
        expected_state: Expected state parameter for CSRF protection

    Returns:
        Tuple of (auth_code, error_message)
    """
    # Reset handler state
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.error_message = None
    OAuthCallbackHandler.received_callback.clear()
    OAuthCallbackHandler.expected_state = expected_state

    # Create and start server
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    server.timeout = 1  # Check for shutdown every second

    # Run server in a thread
    def serve():
        start_time = time.time()
        while not OAuthCallbackHandler.received_callback.is_set():
            server.handle_request()
            if time.time() - start_time > timeout:
                OAuthCallbackHandler.error_message = "Timeout waiting for authorization"
                break

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()

    # Wait for callback or timeout
    OAuthCallbackHandler.received_callback.wait(timeout)

    return OAuthCallbackHandler.auth_code, OAuthCallbackHandler.error_message


def exchange_code_for_tokens(config: OAuthConfig, auth_code: str) -> TokenData:
    """
    Exchange authorization code for access and refresh tokens

    Args:
        config: OAuth configuration
        auth_code: Authorization code from callback

    Returns:
        TokenData with access and refresh tokens

    Raises:
        Exception: If token exchange fails
    """
    token_url = "https://api.smartthings.com/oauth/token"

    # SmartThings requires Basic Auth (client_id:client_secret in Authorization header)
    auth_string = f"{config.client_id}:{config.client_secret}"
    auth_b64 = base64.b64encode(auth_string.encode()).decode()

    # Prepare form data (NO client credentials in body)
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": config.redirect_uri,
    }

    # Make token exchange request with Basic Auth
    with httpx.Client() as client:
        response = client.post(
            token_url,
            data=data,
            headers={
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    if response.status_code != 200:
        # Sanitize error messages - don't expose full response
        error_msg = f"Token exchange failed (HTTP {response.status_code})"
        try:
            error_json = response.json()
            # Only include specific error codes if available
            if "error" in error_json:
                error_msg = f"{error_msg}: {error_json['error']}"
            if "error_description" in error_json:
                # Limit description length for security
                desc = error_json["error_description"][:100]
                error_msg = f"{error_msg} - {desc}"
        except Exception:
            # Don't expose raw response text
            pass
        raise Exception(error_msg)

    # Parse response
    token_response = response.json()

    # Calculate expiration time
    expires_in = token_response.get("expires_in", 86400)  # Default to 24 hours
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in)

    # Create TokenData
    return TokenData(
        access_token=token_response["access_token"],
        refresh_token=token_response.get("refresh_token", ""),
        expires_at=expires_at.isoformat(),
        obtained_at=now.isoformat(),
        token_type=token_response.get("token_type", "Bearer"),
        scope=token_response.get("scope"),
    )


def run_oauth_flow(config: OAuthConfig) -> TokenData:
    """
    Run complete OAuth authorization flow

    Args:
        config: OAuth configuration

    Returns:
        TokenData with tokens

    Raises:
        Exception: If authorization fails
    """
    # Generate CSRF state parameter
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    auth_url = "https://api.smartthings.com/oauth/authorize"
    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": "r:devices:* x:devices:* r:locations:*",
        "state": state,  # Add state parameter for CSRF protection
    }
    full_auth_url = f"{auth_url}?{urllib.parse.urlencode(params)}"

    print("\n" + "=" * 60)
    print("SmartThings OAuth Authorization")
    print("=" * 60)
    print("\nOpening your browser for authorization...")
    print(f"If the browser doesn't open, visit this URL:\n\n{full_auth_url}\n")

    # Extract port from redirect URI
    parsed_redirect = urllib.parse.urlparse(config.redirect_uri)
    port = parsed_redirect.port or 8080

    # Start callback server FIRST (before opening browser)
    print(f"\nStarting callback server on http://localhost:{port}/callback...")

    # Start server in background
    server_started = threading.Event()
    auth_result = {}

    def run_server():
        server_started.set()
        auth_code, error = start_callback_server(
            port=port, expected_state=state, timeout=300
        )
        auth_result["code"] = auth_code
        auth_result["error"] = error

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait for server to start
    server_started.wait(timeout=2)
    print("✓ Callback server ready")

    # NOW open browser
    print("\nOpening your browser for authorization...")
    print("(This will timeout in 5 minutes)")
    webbrowser.open(full_auth_url)

    # Wait for callback to complete
    server_thread.join(timeout=310)

    auth_code = auth_result.get("code")
    error = auth_result.get("error")

    if error:
        raise Exception(f"Authorization failed: {error}")

    if not auth_code:
        raise Exception("No authorization code received")

    print("\nAuthorization code received! Exchanging for tokens...")

    # Exchange code for tokens
    tokens = exchange_code_for_tokens(config, auth_code)

    return tokens


def main():
    """Main CLI entry point for OAuth setup"""
    print("\nSmartThings MCP OAuth Setup")
    print("=" * 40)

    # Load configuration from environment variables
    client_id = os.environ.get("SMARTTHINGS_CLIENT_ID")
    client_secret = os.environ.get("SMARTTHINGS_CLIENT_SECRET")

    # Check required environment variables
    if not client_id or not client_secret:
        print("\nError: Required environment variables not set!")
        print("\nPlease set the following environment variables:")
        print("  - SMARTTHINGS_CLIENT_ID")
        print("  - SMARTTHINGS_CLIENT_SECRET")
        print("\nYou can obtain these from the SmartThings Developer Workspace:")
        print("https://smartthings.developer.samsung.com/workspace/projects")
        print("\nExample:")
        print("  export SMARTTHINGS_CLIENT_ID='your-client-id'")
        print("  export SMARTTHINGS_CLIENT_SECRET='your-client-secret'")
        sys.exit(1)

    # Optional configuration
    redirect_uri = os.environ.get(
        "SMARTTHINGS_REDIRECT_URI", "http://localhost:8080/callback"
    )
    token_file = os.environ.get(
        "SMARTTHINGS_TOKEN_FILE", "~/.config/smartthings-mcp/tokens.json"
    )

    # Create configuration
    config = OAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        token_file_path=token_file,
    )

    print(f"\nConfiguration:")
    print(
        f"  Client ID: {client_id[:8]}..."
        if len(client_id) > 8
        else f"  Client ID: {client_id}"
    )
    print(f"  Redirect URI: {redirect_uri}")
    print(f"  Token file: {os.path.expanduser(token_file)}")

    try:
        # Run OAuth flow
        tokens = run_oauth_flow(config)

        # Save tokens
        token_manager = TokenManager(config)
        token_manager.save_tokens(tokens)

        # Display success
        print("\n" + "=" * 60)
        print("Success! OAuth tokens have been saved.")
        print("=" * 60)
        print(f"\nTokens saved to: {os.path.expanduser(config.token_file_path)}")
        print(f"Token expires at: {tokens.expires_at}")

        if tokens.scope:
            print(f"Authorized scopes: {tokens.scope}")

        print("\nYou can now use SmartThings MCP with OAuth authentication!")
        print("\nTo use the tokens in your application:")
        print("  1. Set SMARTTHINGS_CLIENT_ID and SMARTTHINGS_CLIENT_SECRET")
        print("  2. The TokenManager will automatically load saved tokens")

    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        print("\nPlease check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
