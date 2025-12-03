#!/usr/bin/env python3
"""Control SmartThings light brightness, color temperature, and color."""

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


def set_level(client: SmartThingsClient, device_ids: list, level: int) -> dict:
    """Set brightness level (0-100%)."""
    results = {}
    for device_id in device_ids:
        try:
            client.execute_command(device_id, "switchLevel", "setLevel", [level])
            results[device_id] = {"success": True, "level": level}
        except Exception as e:
            results[device_id] = {"success": False, "error": str(e)}
    return results


def set_color_temp(client: SmartThingsClient, device_ids: list, temperature: int) -> dict:
    """Set color temperature in Kelvin."""
    results = {}
    for device_id in device_ids:
        try:
            client.execute_command(device_id, "colorTemperature", "setColorTemperature", [temperature])
            results[device_id] = {"success": True, "temperature": temperature}
        except Exception as e:
            results[device_id] = {"success": False, "error": str(e)}
    return results


def set_color(client: SmartThingsClient, device_ids: list, hue: int, saturation: int) -> dict:
    """Set color using hue (0-100%) and saturation (0-100%)."""
    results = {}
    for device_id in device_ids:
        try:
            client.execute_command(device_id, "colorControl", "setColor", [{"hue": hue, "saturation": saturation}])
            results[device_id] = {"success": True, "hue": hue, "saturation": saturation}
        except Exception as e:
            results[device_id] = {"success": False, "error": str(e)}
    return results


def set_fade(client: SmartThingsClient, device_ids: list, duration: int, start_level: int, end_level: int, color_temp: int = 2500, turn_off_after: bool = True) -> dict:
    """Configure fade effect for sleep/wake transitions."""
    results = {}
    fade_config = {
        "duration": duration,
        "startLevel": start_level,
        "endLevel": end_level,
        "colorTemp": color_temp,
        "turnOffAfter": turn_off_after,
    }
    for device_id in device_ids:
        try:
            client.execute_command(device_id, "synthetic.lightingEffectFade", "setFade", [fade_config])
            results[device_id] = {"success": True, "fade": fade_config}
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

        if command == "level":
            level = data.get("level")
            if level is None or not (0 <= level <= 100):
                print(json.dumps({"success": False, "error": "level must be 0-100"}))
                sys.exit(1)
            results = set_level(client, device_ids, level)

        elif command == "color_temp":
            temperature = data.get("temperature")
            if temperature is None:
                print(json.dumps({"success": False, "error": "temperature is required"}))
                sys.exit(1)
            results = set_color_temp(client, device_ids, temperature)

        elif command == "color":
            hue = data.get("hue")
            saturation = data.get("saturation")
            if hue is None or saturation is None:
                print(json.dumps({"success": False, "error": "hue and saturation are required"}))
                sys.exit(1)
            if not (0 <= hue <= 100) or not (0 <= saturation <= 100):
                print(json.dumps({"success": False, "error": "hue and saturation must be 0-100"}))
                sys.exit(1)
            results = set_color(client, device_ids, hue, saturation)

        elif command == "fade":
            duration = data.get("duration")
            start_level = data.get("start_level")
            end_level = data.get("end_level")
            color_temp = data.get("color_temp", 2500)
            turn_off_after = data.get("turn_off_after", True)

            if None in (duration, start_level, end_level):
                print(json.dumps({"success": False, "error": "duration, start_level, and end_level are required"}))
                sys.exit(1)
            results = set_fade(client, device_ids, duration, start_level, end_level, color_temp, turn_off_after)

        else:
            print(json.dumps({"success": False, "error": "command must be 'level', 'color_temp', 'color', or 'fade'"}))
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
