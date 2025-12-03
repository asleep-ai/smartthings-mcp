#!/usr/bin/env python3
"""List all SmartThings devices with switch capability."""

import json
import os
import sys

from smartthings_mcp.client import SmartThingsClient
from smartthings_mcp.oauth import OAuthConfig, TokenManager


def get_client() -> SmartThingsClient:
    """Initialize SmartThings client with OAuth authentication."""
    config = OAuthConfig(
        client_id=os.environ["SMARTTHINGS_CLIENT_ID"],
        client_secret=os.environ["SMARTTHINGS_CLIENT_SECRET"],
    )
    token_manager = TokenManager(config)
    return SmartThingsClient(token_manager=token_manager)


def main():
    try:
        client = get_client()
        devices = client.get_devices()

        # Format device list
        result = []
        for device in devices:
            result.append({
                "id": device.get("deviceId"),
                "label": device.get("label"),
                "name": device.get("name"),
                "type": device.get("type"),
                "capabilities": [
                    cap.get("id")
                    for comp in device.get("components", [])
                    for cap in comp.get("capabilities", [])
                ],
            })

        print(json.dumps({"success": True, "devices": result}, indent=2))

    except KeyError as e:
        print(json.dumps({"success": False, "error": f"Missing environment variable: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
