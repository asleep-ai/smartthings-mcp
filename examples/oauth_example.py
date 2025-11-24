#!/usr/bin/env python3
"""Simple example of using SmartThings MCP with OAuth authentication."""

import os
from smartthings_mcp.oauth import OAuthConfig, TokenManager
from smartthings_mcp.client import SmartThingsClient


def main():
    # Configure OAuth
    config = OAuthConfig(
        client_id=os.environ["SMARTTHINGS_CLIENT_ID"],
        client_secret=os.environ["SMARTTHINGS_CLIENT_SECRET"],
    )

    # Initialize token manager and client
    token_manager = TokenManager(config)
    client = SmartThingsClient(token_manager=token_manager)

    # List all devices
    devices = client.get_devices()
    print(f"Found {len(devices)} device(s):")

    for device in devices:
        print(f"  - {device['label']} ({device['deviceId']})")

        # Turn on switches
        if any(c.get('id') == 'switch'
               for component in device.get('components', [])
               for c in component.get('capabilities', [])):
            client.execute_command(device['deviceId'], 'switch', 'on')
            print(f"    ✓ Turned on")


if __name__ == "__main__":
    main()
