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
                    description="Turn on SmartThings switches",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            }
                        },
                        "required": ["device_ids"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="turn_off",
                    description="Turn off SmartThings switches",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            }
                        },
                        "required": ["device_ids"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_cooling_setpoint",
                    description="Set cooling temperature for air conditioners",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            },
                            "temperature": {
                                "type": "number",
                                "description": "The cooling temperature setpoint",
                            },
                        },
                        "required": ["device_ids", "temperature"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_air_conditioner_mode",
                    description="Set the mode for air conditioners",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            },
                            "mode": {
                                "type": "string",
                                "description": "The air conditioner mode (common modes: cool, heat, auto, dry, fan - varies by device)",
                            },
                        },
                        "required": ["device_ids", "mode"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="get_device_status",
                    description="Get the current status of SmartThings devices, showing all capability values",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            }
                        },
                        "required": ["device_ids"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_humidifier_mode",
                    description="Set the humidifier mode on SmartThings devices",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            },
                            "mode": {
                                "type": "string",
                                "description": "The humidifier mode to set (common modes: auto, low, medium, high - varies by device)",
                            },
                        },
                        "required": ["device_ids", "mode"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_switch_level",
                    description="Set brightness level of SmartThings lights (0-100%)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            },
                            "level": {
                                "type": "integer",
                                "description": "Brightness level (0-100%)",
                                "minimum": 0,
                                "maximum": 100,
                            },
                        },
                        "required": ["device_ids", "level"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_color_temperature",
                    description="Set color temperature of SmartThings lights in Kelvin (lower=warm, higher=cool)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            },
                            "temperature": {
                                "type": "integer",
                                "description": "Color temperature in Kelvin (typical range: 2000-6500K, varies by device)",
                            },
                        },
                        "required": ["device_ids", "temperature"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_color",
                    description="Set color of SmartThings lights using hue and saturation (0-100% each)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            },
                            "hue": {
                                "type": "integer",
                                "description": "Hue as percentage (0-100%, where 0=red, 33=green, 67=blue)",
                                "minimum": 0,
                                "maximum": 100,
                            },
                            "saturation": {
                                "type": "integer",
                                "description": "Saturation as percentage (0-100%, where 0=white, 100=full color)",
                                "minimum": 0,
                                "maximum": 100,
                            },
                        },
                        "required": ["device_ids", "hue", "saturation"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_light_fade",
                    description="Configure fade effect for sleep/wake lighting transitions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
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
                        "required": ["device_ids", "duration", "start_level", "end_level"],
                        "additionalProperties": False,
                    },
                ),
                Tool(
                    name="set_fan_mode",
                    description="Set fan mode for air conditioners or air purifiers (e.g., smart, max, medium, sleep, auto)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of SmartThings device IDs",
                                "minItems": 1,
                                "maxItems": 10,
                            },
                            "mode": {
                                "type": "string",
                                "description": "Fan mode (common modes: auto, low, medium, high, smart, sleep, turbo - varies by device)",
                            },
                        },
                        "required": ["device_ids", "mode"],
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
                    device_ids = arguments.get("device_ids")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    return await self._turn_on(device_ids)
                elif name == "turn_off":
                    device_ids = arguments.get("device_ids")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    return await self._turn_off(device_ids)
                elif name == "set_cooling_setpoint":
                    device_ids = arguments.get("device_ids")
                    temperature = arguments.get("temperature")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    if temperature is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: temperature parameter is required",
                            )
                        ]
                    return await self._set_cooling_setpoint(device_ids, temperature)
                elif name == "set_air_conditioner_mode":
                    device_ids = arguments.get("device_ids")
                    mode = arguments.get("mode")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    if not mode:
                        return [
                            TextContent(
                                type="text",
                                text="Error: mode parameter is required",
                            )
                        ]
                    return await self._set_air_conditioner_mode(device_ids, mode)
                elif name == "get_device_status":
                    device_ids = arguments.get("device_ids")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    return await self._get_device_status(device_ids)
                elif name == "set_humidifier_mode":
                    device_ids = arguments.get("device_ids")
                    mode = arguments.get("mode")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    if not mode:
                        return [
                            TextContent(
                                type="text",
                                text="Error: mode parameter is required",
                            )
                        ]
                    return await self._set_humidifier_mode(device_ids, mode)
                elif name == "set_switch_level":
                    device_ids = arguments.get("device_ids")
                    level = arguments.get("level")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    if level is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: level parameter is required",
                            )
                        ]
                    return await self._set_switch_level(device_ids, level)
                elif name == "set_color_temperature":
                    device_ids = arguments.get("device_ids")
                    temperature = arguments.get("temperature")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    if temperature is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: temperature parameter is required",
                            )
                        ]
                    return await self._set_color_temperature(device_ids, temperature)
                elif name == "set_color":
                    device_ids = arguments.get("device_ids")
                    hue = arguments.get("hue")
                    saturation = arguments.get("saturation")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    if hue is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: hue parameter is required",
                            )
                        ]
                    if saturation is None:
                        return [
                            TextContent(
                                type="text",
                                text="Error: saturation parameter is required",
                            )
                        ]
                    return await self._set_color(device_ids, hue, saturation)
                elif name == "set_light_fade":
                    device_ids = arguments.get("device_ids")
                    duration = arguments.get("duration")
                    start_level = arguments.get("start_level")
                    end_level = arguments.get("end_level")
                    color_temp = arguments.get("color_temp", 2500)
                    turn_off_after = arguments.get("turn_off_after", True)
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
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
                        device_ids, duration, start_level, end_level, color_temp, turn_off_after
                    )
                elif name == "set_fan_mode":
                    device_ids = arguments.get("device_ids")
                    mode = arguments.get("mode")
                    if not device_ids:
                        return [
                            TextContent(
                                type="text",
                                text="Error: device_ids parameter is required",
                            )
                        ]
                    if not mode:
                        return [
                            TextContent(
                                type="text",
                                text="Error: mode parameter is required",
                            )
                        ]
                    return await self._set_fan_mode(device_ids, mode)
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

    def _format_batch_results(self, results: List[Dict[str, str]]) -> str:
        """Format batch operation results."""
        lines = []
        success_count = sum(1 for r in results if r["status"] == "success")
        lines.append(f"Results: {success_count}/{len(results)} succeeded\n")
        for result in results:
            status_icon = "OK" if result["status"] == "success" else "FAILED"
            lines.append(f"- {result['device_id']}: {status_icon} - {result['message']}")
        return "\n".join(lines)

    def _parse_error_message(
        self, error: Exception, capability_name: str = "this capability"
    ) -> str:
        """Parse exception and return user-friendly error message."""
        error_msg = str(error)
        if "404" in error_msg or "not found" in error_msg.lower():
            return "Device not found"
        elif "422" in error_msg or "Invalid command" in error_msg:
            return f"Device does not support {capability_name}"
        return error_msg

    async def _turn_on(self, device_ids: List[str]) -> List[TextContent]:
        """Turn on SmartThings switches."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None, self.client.execute_command, device_id, "switch", "on"
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": "Turned on",
                }
            except Exception as e:
                logger.error(f"Failed to turn on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "switch capability"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _turn_off(self, device_ids: List[str]) -> List[TextContent]:
        """Turn off SmartThings switches."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None, self.client.execute_command, device_id, "switch", "off"
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": "Turned off",
                }
            except Exception as e:
                logger.error(f"Failed to turn off device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "switch capability"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _set_cooling_setpoint(
        self, device_ids: List[str], temperature: float
    ) -> List[TextContent]:
        """Set cooling temperature for air conditioners."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None,
                    self.client.execute_command,
                    device_id,
                    "thermostatCoolingSetpoint",
                    "setCoolingSetpoint",
                    [temperature],
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": f"Set cooling setpoint to {temperature}",
                }
            except Exception as e:
                logger.error(f"Failed to set cooling setpoint on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "thermostatCoolingSetpoint"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _set_air_conditioner_mode(
        self, device_ids: List[str], mode: str
    ) -> List[TextContent]:
        """Set the mode for air conditioners."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None,
                    self.client.execute_command,
                    device_id,
                    "airConditionerMode",
                    "setAirConditionerMode",
                    [mode],
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": f"Set mode to '{mode}'",
                }
            except Exception as e:
                logger.error(f"Failed to set AC mode on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "airConditionerMode"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _get_device_status(self, device_ids: List[str]) -> List[TextContent]:
        """Get the current status of SmartThings devices."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> str:
            try:
                status = await loop.run_in_executor(
                    None, self.client.get_device_status, device_id
                )

                # Format the status response nicely
                response_lines = [f"\n=== Device {device_id} ==="]

                components = status.get("components", {})
                for component_name, capabilities in components.items():
                    if component_name != "main":
                        response_lines.append(f"\nComponent: {component_name}")

                    for capability_name, attributes in capabilities.items():
                        for attr_name, attr_data in attributes.items():
                            value = attr_data.get("value")
                            unit = attr_data.get("unit", "")

                            if unit:
                                formatted_value = f"{value}{unit}"
                            elif value is None:
                                formatted_value = "null"
                            else:
                                formatted_value = str(value)

                            response_lines.append(
                                f"- {capability_name}.{attr_name}: {formatted_value}"
                            )

                return "\n".join(response_lines)

            except Exception as e:
                logger.error(f"Failed to get status for device {device_id}: {e}")
                error_msg = self._parse_error_message(e)
                return f"\n=== Device {device_id} ===\nFAILED: {error_msg}"

        tasks = [execute_single(device_id) for device_id in device_ids]
        all_results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text="\n".join(all_results))]

    async def _set_humidifier_mode(
        self, device_ids: List[str], mode: str
    ) -> List[TextContent]:
        """Set the humidifier mode on SmartThings devices."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None,
                    self.client.execute_command,
                    device_id,
                    "humidifierMode",
                    "setHumidifierMode",
                    [mode],
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": f"Set humidifier mode to '{mode}'",
                }
            except Exception as e:
                logger.error(f"Failed to set humidifier mode on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "humidifierMode"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _set_switch_level(
        self, device_ids: List[str], level: int
    ) -> List[TextContent]:
        """Set brightness level of SmartThings lights."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None,
                    self.client.execute_command,
                    device_id,
                    "switchLevel",
                    "setLevel",
                    [level],
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": f"Set brightness to {level}%",
                }
            except Exception as e:
                logger.error(f"Failed to set switch level on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "switchLevel"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _set_color_temperature(
        self, device_ids: List[str], temperature: int
    ) -> List[TextContent]:
        """Set color temperature of SmartThings lights."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None,
                    self.client.execute_command,
                    device_id,
                    "colorTemperature",
                    "setColorTemperature",
                    [temperature],
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": f"Set color temperature to {temperature}K",
                }
            except Exception as e:
                logger.error(f"Failed to set color temperature on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "colorTemperature"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _set_color(
        self, device_ids: List[str], hue: int, saturation: int
    ) -> List[TextContent]:
        """Set color of SmartThings lights using hue and saturation."""
        loop = asyncio.get_event_loop()
        color_map = {"hue": hue, "saturation": saturation}

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None,
                    self.client.execute_command,
                    device_id,
                    "colorControl",
                    "setColor",
                    [color_map],
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": f"Set color to hue={hue}%, saturation={saturation}%",
                }
            except Exception as e:
                logger.error(f"Failed to set color on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "colorControl"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _set_light_fade(
        self,
        device_ids: List[str],
        duration: int,
        start_level: int,
        end_level: int,
        color_temp: int = 2500,
        turn_off_after: bool = True,
    ) -> List[TextContent]:
        """Configure fade effect for sleep/wake lighting transitions."""
        loop = asyncio.get_event_loop()

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
        fade_type = "wind down" if end_level < start_level else "wake up"

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None,
                    self.client.execute_command,
                    device_id,
                    "synthetic.lightingEffectFade",
                    "setFade",
                    [fade_config],
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": f"Configured {fade_type} fade: {start_level}% -> {end_level}% over {duration}min",
                }
            except Exception as e:
                logger.error(f"Failed to set light fade on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "lightingEffectFade"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

    async def _set_fan_mode(
        self, device_ids: List[str], mode: str
    ) -> List[TextContent]:
        """Set fan mode for air conditioners or air purifiers."""
        loop = asyncio.get_event_loop()

        async def execute_single(device_id: str) -> Dict[str, str]:
            try:
                await loop.run_in_executor(
                    None,
                    self.client.execute_command,
                    device_id,
                    "airConditionerFanMode",
                    "setFanMode",
                    [mode],
                )
                return {
                    "device_id": device_id,
                    "status": "success",
                    "message": f"Set fan mode to '{mode}'",
                }
            except Exception as e:
                logger.error(f"Failed to set fan mode on device {device_id}: {e}")
                return {
                    "device_id": device_id,
                    "status": "failed",
                    "message": self._parse_error_message(e, "airConditionerFanMode"),
                }

        tasks = [execute_single(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)

        return [TextContent(type="text", text=self._format_batch_results(list(results)))]

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
