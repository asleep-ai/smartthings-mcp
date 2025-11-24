"""
Minimal SmartThings API client for MCP integration
"""

import httpx
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .oauth import TokenManager


class SmartThingsClient:
    """SmartThings API client with support for both PAT and OAuth authentication"""

    def __init__(self, api_token: Optional[str] = None,
                 token_manager: Optional['TokenManager'] = None):
        """
        Initialize SmartThings client with either PAT or OAuth authentication

        Args:
            api_token: SmartThings Personal Access Token (for PAT authentication)
            token_manager: TokenManager instance (for OAuth authentication)

        Raises:
            ValueError: If neither api_token nor token_manager is provided
        """
        if not api_token and not token_manager:
            raise ValueError("Either api_token or token_manager must be provided")

        self.api_token = api_token
        self.token_manager = token_manager
        self.auth_mode = "pat" if api_token else "oauth"
        self.base_url = "https://api.smartthings.com/v1"
        self.client = httpx.Client()  # Initialize without headers - will pass them per request

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers with Bearer authentication

        Returns:
            Headers dict with Authorization Bearer token

        Note:
            In OAuth mode, automatically refreshes token if needed
        """
        # Get the appropriate token based on auth mode
        if self.auth_mode == "pat":
            token = self.api_token
        else:
            # OAuth mode - get valid token (auto-refreshes if needed)
            token = self.token_manager.get_valid_token()

        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get all devices from SmartThings

        Returns:
            List of device dictionaries

        Raises:
            Exception: If API request fails
        """
        response = self.client.get(
            f"{self.base_url}/devices",
            headers=self._get_headers()  # Pass fresh headers with current token
        )

        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            raise Exception(f"Failed to get devices: {response.status_code} - {response.text}")

    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Get current status of a specific device

        Args:
            device_id: SmartThings device ID

        Returns:
            Device status dictionary containing capabilities and their current values

        Raises:
            Exception: If API request fails
        """
        response = self.client.get(
            f"{self.base_url}/devices/{device_id}/status",
            headers=self._get_headers()  # Pass fresh headers with current token
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get device status: {response.status_code} - {response.text}")

    def execute_command(self, device_id: str, capability: str, command: str,
                       args: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute a command on a device

        Args:
            device_id: SmartThings device ID
            capability: Capability name (e.g., "switch", "switchLevel")
            command: Command name (e.g., "on", "off", "setLevel")
            args: Optional list of arguments for the command

        Returns:
            Command execution result

        Raises:
            Exception: If API request fails
        """
        # Build command payload
        command_payload = {
            "component": "main",
            "capability": capability,
            "command": command
        }

        if args:
            command_payload["arguments"] = args

        # SmartThings expects commands as a list
        payload = {
            "commands": [command_payload]
        }

        response = self.client.post(
            f"{self.base_url}/devices/{device_id}/commands",
            json=payload,
            headers=self._get_headers()  # Pass fresh headers with current token
        )

        if response.status_code in [200, 202]:
            # Some commands return empty response on success
            return response.json() if response.text else {"status": "success"}
        else:
            raise Exception(f"Failed to execute command: {response.status_code} - {response.text}")