#!/usr/bin/env python3
"""Test script to verify the SmartThings MCP server implementation."""

import sys
import os

# Add src to path for local testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from smartthings_mcp.client import SmartThingsClient


def test_client():
    """Test the SmartThings client directly."""
    token = os.environ.get("SMARTTHINGS_TOKEN")

    if not token:
        print("Error: SMARTTHINGS_TOKEN environment variable not set")
        print("\nTo get your PAT token:")
        print("1. Go to: https://account.smartthings.com/tokens")
        print("2. Sign in and generate a new token")
        print("3. Export it: export SMARTTHINGS_TOKEN='your-token-here'")
        return

    try:
        # Create client
        client = SmartThingsClient(token)
        print("✓ Client initialized successfully")

        # Test getting devices
        print("\nFetching devices...")
        devices = client.get_devices()
        print(f"✓ Found {len(devices)} devices")

        # Filter for devices with switch capability
        switch_devices = []
        for device in devices:
            components = device.get("components", [])
            for component in components:
                capabilities = component.get("capabilities", [])
                for capability in capabilities:
                    if capability.get("id") == "switch":
                        switch_devices.append(device)
                        break

        print(f"✓ Found {len(switch_devices)} devices with switch capability")

        # List switch devices
        if switch_devices:
            print("\nSwitch devices:")
            for device in switch_devices[:5]:  # Show first 5
                print(f"  - {device.get('label', 'Unknown')} (ID: {device.get('deviceId')})")

            # Test getting device status
            if switch_devices:
                test_device = switch_devices[0]
                device_id = test_device.get("deviceId")
                print(f"\nTesting device status for: {test_device.get('label')}")

                try:
                    status = client.get_device_status(device_id)
                    print("✓ Device status retrieved successfully")

                    # Check switch status
                    components = status.get("components", {})
                    main_component = components.get("main", {})
                    switch_status = main_component.get("switch", {})
                    switch_value = switch_status.get("switch", {}).get("value")
                    if switch_value:
                        print(f"  Current switch status: {switch_value}")
                except Exception as e:
                    print(f"✗ Failed to get device status: {e}")
        else:
            print("\nNo devices with switch capability found")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("SmartThings MCP Server Test")
    print("=" * 40)
    test_client()