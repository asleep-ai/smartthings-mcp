#!/usr/bin/env python3
"""Get current status of SmartThings devices."""

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
        data = json.load(sys.stdin)
        device_ids = data.get("device_ids", [])

        if not device_ids:
            print(json.dumps({"success": False, "error": "device_ids is required"}))
            sys.exit(1)

        if len(device_ids) > 10:
            print(json.dumps({"success": False, "error": "Maximum 10 devices per request"}))
            sys.exit(1)

        client = get_client()
        results = {}

        for device_id in device_ids:
            try:
                status = client.get_device_status(device_id)
                results[device_id] = {"success": True, "status": status}
            except Exception as e:
                results[device_id] = {"success": False, "error": str(e)}

        print(json.dumps({"success": True, "results": results}, indent=2))

    except json.JSONDecodeError:
        print(json.dumps({"success": False, "error": "Invalid JSON input"}))
        sys.exit(1)
    except KeyError as e:
        print(json.dumps({"success": False, "error": f"Missing environment variable: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
