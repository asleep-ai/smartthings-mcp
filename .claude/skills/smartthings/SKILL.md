---
name: smartthings
description: Control SmartThings smart home devices including lights, switches, thermostats, air conditioners, and fans. Use when user mentions smart home, lights, AC, temperature, turning devices on/off, brightness, color, or device status.
---

# SmartThings Device Control

Control Samsung SmartThings connected devices via Python scripts that use the SmartThings API.

## Prerequisites

Environment variables required:
- `SMARTTHINGS_CLIENT_ID` - OAuth client ID
- `SMARTTHINGS_CLIENT_SECRET` - OAuth client secret

OAuth tokens are automatically refreshed and stored at `~/.config/smartthings-mcp/tokens.json`.

## Available Scripts

All scripts are in the `scripts/` directory and accept JSON input via stdin.

### list_devices.py
List all SmartThings devices with switch capability.

```bash
echo '{}' | python scripts/list_devices.py
```

Returns: Array of devices with id, label, and capabilities.

### device_status.py
Get current status of devices.

```bash
echo '{"device_ids": ["device-id-1", "device-id-2"]}' | python scripts/device_status.py
```

Input:
- `device_ids`: Array of device IDs (1-10)

### switch_control.py
Turn devices on or off.

```bash
echo '{"action": "on", "device_ids": ["device-id-1"]}' | python scripts/switch_control.py
```

Input:
- `action`: "on" or "off"
- `device_ids`: Array of device IDs (1-10)

### light_control.py
Control light brightness, color temperature, and color.

```bash
# Set brightness
echo '{"command": "level", "device_ids": ["id"], "level": 75}' | python scripts/light_control.py

# Set color temperature
echo '{"command": "color_temp", "device_ids": ["id"], "temperature": 3000}' | python scripts/light_control.py

# Set color (hue/saturation)
echo '{"command": "color", "device_ids": ["id"], "hue": 67, "saturation": 100}' | python scripts/light_control.py

# Set fade effect
echo '{"command": "fade", "device_ids": ["id"], "duration": 30, "start_level": 100, "end_level": 0, "color_temp": 2500}' | python scripts/light_control.py
```

Input for each command:
- `level`: brightness 0-100%
- `color_temp`: temperature in Kelvin (2000-6500 typical)
- `color`: hue (0-100%, 0=red, 33=green, 67=blue), saturation (0-100%)
- `fade`: duration (minutes), start_level, end_level, color_temp (optional), turn_off_after (optional, default true)

### climate_control.py
Control air conditioners, fans, and humidifiers.

```bash
# Set cooling temperature
echo '{"command": "cooling", "device_ids": ["id"], "temperature": 72}' | python scripts/climate_control.py

# Set AC mode
echo '{"command": "ac_mode", "device_ids": ["id"], "mode": "cool"}' | python scripts/climate_control.py

# Set fan mode
echo '{"command": "fan_mode", "device_ids": ["id"], "mode": "auto"}' | python scripts/climate_control.py

# Set humidifier mode
echo '{"command": "humidifier_mode", "device_ids": ["id"], "mode": "auto"}' | python scripts/climate_control.py
```

AC modes: cool, heat, auto, dry, fan (varies by device)
Fan modes: auto, low, medium, high, smart, sleep, turbo (varies by device)

## Common Workflows

### Turn on all lights
1. Run `list_devices.py` to get device IDs
2. Filter for light devices
3. Run `switch_control.py` with action "on"

### Set bedroom for sleep
1. Get bedroom light IDs from `list_devices.py`
2. Run `light_control.py` with fade command:
   - start_level: 100
   - end_level: 0
   - duration: 30
   - color_temp: 2500 (warm)

### Check device status
1. Get device IDs from `list_devices.py`
2. Run `device_status.py` with those IDs

## Error Handling

Scripts return JSON with either:
- Success: `{"success": true, "result": ...}`
- Error: `{"success": false, "error": "message"}`

Common errors:
- Device not found (404)
- Unsupported capability (422)
- Rate limited (429) - max 12 requests/minute per device
