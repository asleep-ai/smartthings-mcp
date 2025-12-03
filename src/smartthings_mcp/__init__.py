"""SmartThings MCP Server package."""

import os

# Load .env file if it exists
try:
    from dotenv import load_dotenv

    # Searches current directory and parent directories automatically
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip
    pass

from .client import SmartThingsClient
from .oauth import OAuthConfig, TokenManager
from .server import SmartThingsMCPServer, main

__version__ = "0.1.0"
__all__ = ["SmartThingsMCPServer", "SmartThingsClient", "OAuthConfig", "TokenManager", "main"]
