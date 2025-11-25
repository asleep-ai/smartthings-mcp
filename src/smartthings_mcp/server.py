#!/usr/bin/env python3
"""MCP server for SmartThings switch control."""

import asyncio
import logging
import os
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import SmartThingsClient
from .oauth import OAuthConfig, TokenManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartthings-mcp")


class SmartThingsMCPServer:
    """MCP Server for SmartThings integration."""

    def __init__(self):
        """Initialize the SmartThings MCP server."""
        self.server = Server("smartthings-mcp")
        self.client = None
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP server handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available SmartThings tools."""
            return [
                Tool(
                    name="list_devices",
                    description="List all SmartThings devices with switch capability",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="turn_on",
                    description="Turn on a SmartThings switch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            }
                        },
                        "required": ["device_id"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="turn_off",
                    description="Turn off a SmartThings switch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            }
                        },
                        "required": ["device_id"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_cooling_setpoint",
                    description="Set cooling temperature for an air conditioner",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            },
                            "temperature": {
                                "type": "number",
                                "description": "The cooling temperature setpoint",
                            },
                        },
                        "required": ["device_id", "temperature"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_air_conditioner_mode",
                    description="Set the mode for an air conditioner",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            },
                            "mode": {
                                "type": "string",
                                "description": "The air conditioner mode (common modes: cool, heat, auto, dry, fan - varies by device)",
                            },
                        },
                        "required": ["device_id", "mode"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="get_device_status",
                    description="Get the current status of a SmartThings device, showing all capability values",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            }
                        },
                        "required": ["device_id"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_humidifier_mode",
                    description="Set the humidifier mode on a SmartThings device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            },
                            "mode": {
                                "type": "string",
                                "description": "The humidifier mode to set (common modes: auto, low, medium, high - varies by device)",
                            },
                        },
                        "required": ["device_id", "mode"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_switch_level",
                    description="Set brightness level of a SmartThings light (0-100%)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            },
                            "level": {
                                "type": "integer",
                                "description": "Brightness level (0-100%)",
                                "minimum": 0,
                                "maximum": 100,
                            },
                        },
                        "required": ["device_id", "level"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_color_temperature",
                    description="Set color temperature of a SmartThings light in Kelvin (lower=warm, higher=cool)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            },
                            "temperature": {
                                "type": "integer",
                                "description": "Color temperature in Kelvin (typical range: 2000-6500K, varies by device)",
                            },
                        },
                        "required": ["device_id", "temperature"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_light_fade",
                    description="Configure fade effect for sleep/wake lighting transitions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            },
                            "duration": {
                                "type": "integer",
                                "description": "Fade duration in minutes",
                            },
                            "start_level": {
                                "type": "integer",
                                "description": "Starting brightness level (0-100%)",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "end_level": {
                                "type": "integer",
                                "description": "Ending brightness level (0-100%)",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "color_temp": {
                                "type": "integer",
                                "description": "Color temperature in Kelvin (default: 2500)",
                                "default": 2500,
                            },
                            "turn_off_after": {
                                "type": "boolean",
                                "description": "Turn off light after fade completes (default: true)",
                                "default": True,
                            },
                        },
                        "required": ["device_id", "duration", "start_level", "end_level"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_fan_mode",
                    description="Set fan mode for air conditioner or air purifier (e.g., smart, max, medium, sleep, auto)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "The SmartThings device ID",
                            },
                            "mode": {
                                "type": "string",
                                "description": "Fan mode (common modes: auto, low, medium, high, smart, sleep, turbo - varies by device)",
                            },
                        },
                        "required": ["device_id", "mode"],
                        "additionalProperties": False,
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute a SmartThings tool."""

            # Initialize client if not already done
            if self.client is None:
                # Try OAuth authentication first
                client_id = os.environ.get("SMARTTHINGS_CLIENT_ID")
                client_secret = os.environ.get("SMARTTHINGS_CLIENT_SECRET")

                if client_id and client_secret:
                    # OAuth configuration available
                    try:
                        # Create OAuth config with optional environment overrides
                        redirect_uri = os.environ.get(
                            "SMARTTHINGS_REDIRECT_URI", "http://localhost:8080/callback"
                        )
                        token_file_path = os.environ.get(
                            "SMARTTHINGS_TOKEN_FILE",
                            "~/.config/smartthings-mcp/tokens.json",
                        )

                        oauth_config = OAuthConfig(
                            client_id=client_id,
                            client_secret=client_secret,
                            redirect_uri=redirect_uri,
                            token_file_path=token_file_path,
                        )

                        # Initialize token manager
                        token_manager = TokenManager(oauth_config)

                        # Check if tokens exist (not if they're valid - TokenManager will auto-refresh if expired)
                        if not token_manager.load_tokens():
                            return [
                                TextContent(
                                    type="text",
                                    text="OAuth tokens not found. Run 'python -m smartthings_mcp.oauth_setup' to authenticate.",
                                )
                            ]

                        # Initialize client with OAuth
                        self.client = SmartThingsClient(token_manager=token_manager)
                        logger.info(
                            "Initialized SmartThings client with OAuth authentication"
                        )

                    except Exception as e:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error initializing OAuth client: {str(e)}",
                            )
                        ]
                else:
                    # Fall back to PAT authentication
                    api_token = os.environ.get("SMARTTHINGS_TOKEN")
                    if not api_token:
                        return [
                            TextContent(
                                type="text",
                                text="No authentication configured. Either set SMARTTHINGS_CLIENT_ID + SMARTTHINGS_CLIENT_SECRET for OAuth, or SMARTTHINGS_TOKEN for PAT.",
                            )
                        ]

                    try:
                        self.client = SmartThingsClient(api_token=api_token)
                        logger.info(
                            "Initialized SmartThings client with PAT authentication"
                        )
                    except Exception as e:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error initializing SmartThings client: {str(e)}",
                            )
                        ]

            try:
                if name == "list_devices":
                    return await self._list_devices()
                elif name == "turn_on":
                    device_id = arguments.get("device_id")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    return await self._turn_on(device_id)
                elif name == "turn_off":
                    device_id = arguments.get("device_id")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    return await self._turn_off(device_id)
                elif name == "set_cooling_setpoint":
                    device_id = arguments.get("device_id")
                    temperature = arguments.get("temperature")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    if temperature is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: temperature parameter is required",
                            )
                        ]
                    return await self._set_cooling_setpoint(device_id, temperature)
                elif name == "set_air_conditioner_mode":
                    device_id = arguments.get("device_id")
                    mode = arguments.get("mode")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    if not mode:
                        return [
                            TextContent(
                                type="text",
                                text="Error: mode parameter is required",
                            )
                        ]
                    return await self._set_air_conditioner_mode(device_id, mode)
                elif name == "get_device_status":
                    device_id = arguments.get("device_id")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    return await self._get_device_status(device_id)
                elif name == "set_humidifier_mode":
                    device_id = arguments.get("device_id")
                    mode = arguments.get("mode")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    if not mode:
                        return [
                            TextContent(
                                type="text",
                                text="Error: mode parameter is required",
                            )
                        ]
                    return await self._set_humidifier_mode(device_id, mode)
                elif name == "set_switch_level":
                    device_id = arguments.get("device_id")
                    level = arguments.get("level")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    if level is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: level parameter is required",
                            )
                        ]
                    return await self._set_switch_level(device_id, level)
                elif name == "set_color_temperature":
                    device_id = arguments.get("device_id")
                    temperature = arguments.get("temperature")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    if temperature is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: temperature parameter is required",
                            )
                        ]
                    return await self._set_color_temperature(device_id, temperature)
                elif name == "set_light_fade":
                    device_id = arguments.get("device_id")
                    duration = arguments.get("duration")
                    start_level = arguments.get("start_level")
                    end_level = arguments.get("end_level")
                    color_temp = arguments.get("color_temp", 2500)
                    turn_off_after = arguments.get("turn_off_after", True)
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    if duration is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: duration parameter is required",
                            )
                        ]
                    if start_level is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: start_level parameter is required",
                            )
                        ]
                    if end_level is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: end_level parameter is required",
                            )
                        ]
                    return await self._set_light_fade(
                        device_id, duration, start_level, end_level, color_temp, turn_off_after
                    )
                elif name == "set_fan_mode":
                    device_id = arguments.get("device_id")
                    mode = arguments.get("mode")
                    if not device_id:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_id parameter is required",
                            )
                        ]
                    if not mode:
                        return [
                            TextContent(
                                type="text",
                                text="Error: mode parameter is required",
                            )
                        ]
                    return await self._set_fan_mode(device_id, mode)
                else:
                    return [
                        TextContent(type="text", text=f"Error: Unknown tool '{name}'")
                    ]
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [
                    TextContent(type="text", text=f"Error executing {name}: {str(e)}")
                ]

    async def _list_devices(self) -> List[TextContent]:
        """List all SmartThings devices with switch capability."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            devices = await loop.run_in_executor(None, self.client.get_devices)

            # Filter for devices with switch capability
            switch_devices = []
            for device in devices:
                # Check if device has switch capability
                components = device.get("components", [])
                has_switch = False

                for component in components:
                    capabilities = component.get("capabilities", [])
                    for capability in capabilities:
                        if capability.get("id") == "switch":
                            has_switch = True
                            break
                    if has_switch:
                        break

                if has_switch:
                    # Get room name if available
                    room_name = "No Room"
                    if device.get("roomId"):
                        room_name = f"Room ID: {device.get('roomId')}"

                    switch_devices.append(
                        {
                            "id": device.get("deviceId"),
                            "name": device.get("name", "Unknown"),
                            "label": device.get("label", "Unknown"),
                            "room": room_name,
                        }
                    )

            # Format response
            if not switch_devices:
                return [
                    TextContent(
                        type="text", text="No devices with switch capability found."
                    )
                ]

            response_lines = [
                f"Found {len(switch_devices)} device(s) with switch capability:\n"
            ]
            for device in switch_devices:
                response_lines.append(
                    f"- {device['label']} (ID: {device['id']}, Name: {device['name']}, {device['room']})"
                )

            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            error_msg = f"Failed to list devices: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "401" in str(e) or "Invalid" in str(e).lower():
                error_msg = "Authentication failed. Please check your SMARTTHINGS_TOKEN environment variable."
            elif "Network" in str(e):
                error_msg = "Network error. Please check your internet connection and try again."

            return [TextContent(type="text", text=error_msg)]

    async def _turn_on(self, device_id: str) -> List[TextContent]:
        """Turn on a SmartThings switch."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.client.execute_command, device_id, "switch", "on"
            )

            return [
                TextContent(
                    type="text", text=f"Successfully turned on device {device_id}"
                )
            ]

        except Exception as e:
            error_msg = f"Failed to turn on device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = (
                    f"Device {device_id} does not support the switch capability."
                )

            return [TextContent(type="text", text=error_msg)]

    async def _turn_off(self, device_id: str) -> List[TextContent]:
        """Turn off a SmartThings switch."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.client.execute_command, device_id, "switch", "off"
            )

            return [
                TextContent(
                    type="text", text=f"Successfully turned off device {device_id}"
                )
            ]

        except Exception as e:
            error_msg = f"Failed to turn off device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = (
                    f"Device {device_id} does not support the switch capability."
                )

            return [TextContent(type="text", text=error_msg)]

    async def _set_cooling_setpoint(
        self, device_id: str, temperature: float
    ) -> List[TextContent]:
        """Set cooling temperature for an air conditioner."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.execute_command,
                device_id,
                "thermostatCoolingSetpoint",
                "setCoolingSetpoint",
                [temperature],
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully set cooling setpoint to {temperature} on device {device_id}",
                )
            ]

        except Exception as e:
            error_msg = f"Failed to set cooling setpoint on device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = f"Device {device_id} does not support the thermostatCoolingSetpoint capability."

            return [TextContent(type="text", text=error_msg)]

    async def _set_air_conditioner_mode(
        self, device_id: str, mode: str
    ) -> List[TextContent]:
        """Set the mode for an air conditioner."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.execute_command,
                device_id,
                "airConditionerMode",
                "setAirConditionerMode",
                [mode],
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully set air conditioner mode to '{mode}' on device {device_id}",
                )
            ]

        except Exception as e:
            error_msg = f"Failed to set air conditioner mode on device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = f"Device {device_id} does not support the airConditionerMode capability."

            return [TextContent(type="text", text=error_msg)]

    async def _get_device_status(self, device_id: str) -> List[TextContent]:
        """Get the current status of a SmartThings device."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(
                None, self.client.get_device_status, device_id
            )

            # Format the status response nicely
            response_lines = ["Device Status:"]

            # The status response has a "components" key with component names (usually "main")
            components = status.get("components", {})
            for component_name, capabilities in components.items():
                if component_name != "main":
                    response_lines.append(f"\nComponent: {component_name}")

                for capability_name, attributes in capabilities.items():
                    for attr_name, attr_data in attributes.items():
                        value = attr_data.get("value")
                        unit = attr_data.get("unit", "")

                        # Format the value with unit if present
                        if unit:
                            formatted_value = f"{value}{unit}"
                        elif value is None:
                            formatted_value = "null"
                        else:
                            formatted_value = str(value)

                        response_lines.append(f"- {capability_name}.{attr_name}: {formatted_value}")

            return [TextContent(type="text", text="\n".join(response_lines))]

        except Exception as e:
            error_msg = f"Failed to get device status for {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."

            return [TextContent(type="text", text=error_msg)]

    async def _set_humidifier_mode(
        self, device_id: str, mode: str
    ) -> List[TextContent]:
        """Set the humidifier mode on a SmartThings device."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.execute_command,
                device_id,
                "humidifierMode",
                "setHumidifierMode",
                [mode],
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully set humidifier mode to '{mode}' on device {device_id}",
                )
            ]

        except Exception as e:
            error_msg = f"Failed to set humidifier mode on device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = f"Device {device_id} does not support the humidifierMode capability."

            return [TextContent(type="text", text=error_msg)]

    async def _set_switch_level(
        self, device_id: str, level: int
    ) -> List[TextContent]:
        """Set brightness level of a SmartThings light."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.execute_command,
                device_id,
                "switchLevel",
                "setLevel",
                [level],
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully set brightness to {level}% on device {device_id}",
                )
            ]

        except Exception as e:
            error_msg = f"Failed to set switch level on device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = f"Device {device_id} does not support the switchLevel capability."

            return [TextContent(type="text", text=error_msg)]

    async def _set_color_temperature(
        self, device_id: str, temperature: int
    ) -> List[TextContent]:
        """Set color temperature of a SmartThings light."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.execute_command,
                device_id,
                "colorTemperature",
                "setColorTemperature",
                [temperature],
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully set color temperature to {temperature}K on device {device_id}",
                )
            ]

        except Exception as e:
            error_msg = f"Failed to set color temperature on device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = f"Device {device_id} does not support the colorTemperature capability."

            return [TextContent(type="text", text=error_msg)]

    async def _set_light_fade(
        self,
        device_id: str,
        duration: int,
        start_level: int,
        end_level: int,
        color_temp: int = 2500,
        turn_off_after: bool = True,
    ) -> List[TextContent]:
        """Configure fade effect for sleep/wake lighting transitions."""
        try:
            # Build the fade configuration JSON
            fade_config = {
                "duration": duration,
                "effects": [
                    {"capability": "switchLevel", "start": start_level, "end": end_level},
                    {"capability": "colorTemperature", "start": color_temp, "end": color_temp},
                ],
                "fadeType": "WindDown" if end_level < start_level else "WakeUp",
                "afterAction": {
                    "afterActionType": "TurnOff" if turn_off_after else "DoNothing"
                },
            }

            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.client.execute_command,
                device_id,
                "synthetic.lightingEffectFade",
                "setFade",
                [fade_config],
            )

            fade_type = "wind down" if end_level < start_level else "wake up"
            return [
                TextContent(
                    type="text",
                    text=f"Successfully configured {fade_type} fade on device {device_id}: "
                    f"{start_level}% -> {end_level}% over {duration} minutes at {color_temp}K",
                )
            ]

        except Exception as e:
            error_msg = f"Failed to set light fade on device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = f"Device {device_id} does not support the synthetic.lightingEffectFade capability."

            return [TextContent(type="text", text=error_msg)]

    async def _set_fan_mode(
        self, device_id: str, mode: str
    ) -> List[TextContent]:
        """Set fan mode for air conditioner or air purifier."""
        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.client.execute_command,
                device_id,
                "airConditionerFanMode",
                "setFanMode",
                [mode],
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully set fan mode to '{mode}' on device {device_id}",
                )
            ]

        except Exception as e:
            error_msg = f"Failed to set fan mode on device {device_id}: {str(e)}"
            logger.error(error_msg)

            # Provide helpful error messages
            if "404" in str(e) or "not found" in str(e).lower():
                error_msg = f"Device {device_id} not found. Please check the device ID."
            elif "422" in str(e) or "Invalid command" in str(e):
                error_msg = f"Device {device_id} does not support the airConditionerFanMode capability."

            return [TextContent(type="text", text=error_msg)]

    async def run(self):
        """Run the MCP server."""
        from mcp.server.models import InitializationOptions
        from mcp.types import ServerCapabilities

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="smartthings-mcp",
                    server_version="0.1.0",
                    capabilities=ServerCapabilities(tools={}),
                ),
            )


def main():
    """Main entry point for the SmartThings MCP server."""
    # Check for authentication configuration
    client_id = os.environ.get("SMARTTHINGS_CLIENT_ID")
    client_secret = os.environ.get("SMARTTHINGS_CLIENT_SECRET")
    api_token = os.environ.get("SMARTTHINGS_TOKEN")

    if client_id and client_secret:
        logger.info("OAuth authentication configured. Will use OAuth for API access.")
    elif api_token:
        logger.info(
            "PAT authentication configured. Will use Personal Access Token for API access."
        )
    else:
        logger.warning(
            "No authentication configured. Either set SMARTTHINGS_CLIENT_ID + SMARTTHINGS_CLIENT_SECRET "
            "for OAuth (preferred), or SMARTTHINGS_TOKEN for PAT authentication."
        )

    # Create and run server
    server = SmartThingsMCPServer()

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
