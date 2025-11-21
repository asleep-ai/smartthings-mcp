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
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute a SmartThings tool."""

            # Initialize client if not already done
            if self.client is None:
                api_token = os.environ.get("SMARTTHINGS_TOKEN")
                if not api_token:
                    return [
                        TextContent(
                            type="text",
                            text="Error: SMARTTHINGS_TOKEN environment variable is not set. Please set it with your SmartThings Personal Access Token.",
                        )
                    ]

                try:
                    self.client = SmartThingsClient(api_token)
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
    # Check for API token
    if not os.environ.get("SMARTTHINGS_TOKEN"):
        logger.warning(
            "SMARTTHINGS_TOKEN environment variable is not set. "
            "You will need to set it before using any tools."
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
