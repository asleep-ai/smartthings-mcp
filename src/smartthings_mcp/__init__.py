"""SmartThings MCP Server package."""

from .server import SmartThingsMCPServer, main
from .client import SmartThingsClient

__version__ = "0.1.0"
__all__ = ["SmartThingsMCPServer", "SmartThingsClient", "main"]