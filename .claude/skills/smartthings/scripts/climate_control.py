#!/usr/bin/env python3
"""Control SmartThings air conditioners, fans, and humidifiers."""

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


def set_cooling_setpoint(client: SmartThingsClient, device_ids: list, temperature: float) -> dict:
    """Set cooling temperature setpoint."""
    results = {}
    for device_id in device_ids:
        try:
            client.execute_command(device_id, "thermostatCoolingSetpoint", "setCoolingSetpoint", [temperature])
            results[device_id] = {"success": True, "temperature": temperature}
        except Exception as e:
            results[device_id] = {"success": False, "error": str(e)}
    return results


def set_ac_mode(client: SmartThingsClient, device_ids: list, mode: str) -> dict:
    """Set air conditioner mode (cool, heat, auto, dry, fan)."""
    results = {}
    for device_id in device_ids:
        try:
            client.execute_command(device_id, "airConditionerMode", "setAirConditionerMode", [mode])
            results[device_id] = {"success": True, "mode": mode}
        except Exception as e:
            results[device_id] = {"success": False, "error": str(e)}
    return results


def set_fan_mode(client: SmartThingsClient, device_ids: list, mode: str) -> dict:
    """Set fan mode (auto, low, medium, high, smart, sleep, turbo)."""
    results = {}
    for device_id in device_ids:
        try:
            client.execute_command(device_id, "airConditionerFanMode", "setFanMode", [mode])
            results[device_id] = {"success": True, "mode": mode}
        except Exception as e:
            results[device_id] = {"success": False, "error": str(e)}
    return results


def set_humidifier_mode(client: SmartThingsClient, device_ids: list, mode: str) -> dict:
    """Set humidifier mode (auto, low, medium, high)."""
    results = {}
    for device_id in device_ids:
        try:
            client.execute_command(device_id, "humidifierMode", "setHumidifierMode", [mode])
            results[device_id] = {"success": True, "mode": mode}
        except Exception as e:
            results[device_id] = {"success": False, "error": str(e)}
    return results


def main():
    try:
        data = json.load(sys.stdin)
        command = data.get("command")
        device_ids = data.get("device_ids", [])

        if not device_ids:
            print(json.dumps({"success": False, "error": "device_ids is required"}))
            sys.exit(1)

        if len(device_ids) > 10:
            print(json.dumps({"success": False, "error": "Maximum 10 devices per request"}))
            sys.exit(1)

        client = get_client()

        if command == "cooling":
            temperature = data.get("temperature")
            if temperature is None:
                print(json.dumps({"success": False, "error": "temperature is required"}))
                sys.exit(1)
            results = set_cooling_setpoint(client, device_ids, temperature)

        elif command == "ac_mode":
            mode = data.get("mode")
            if not mode:
                print(json.dumps({"success": False, "error": "mode is required"}))
                sys.exit(1)
            results = set_ac_mode(client, device_ids, mode)

        elif command == "fan_mode":
            mode = data.get("mode")
            if not mode:
                print(json.dumps({"success": False, "error": "mode is required"}))
                sys.exit(1)
            results = set_fan_mode(client, device_ids, mode)

        elif command == "humidifier_mode":
            mode = data.get("mode")
            if not mode:
                print(json.dumps({"success": False, "error": "mode is required"}))
                sys.exit(1)
            results = set_humidifier_mode(client, device_ids, mode)

        else:
            print(json.dumps({
                "success": False,
                "error": "command must be 'cooling', 'ac_mode', 'fan_mode', or 'humidifier_mode'"
            }))
            sys.exit(1)

        success_count = sum(1 for r in results.values() if r.get("success"))
        print(json.dumps({
            "success": True,
            "command": command,
            "summary": f"{success_count}/{len(device_ids)} succeeded",
            "results": results,
        }, indent=2))

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
