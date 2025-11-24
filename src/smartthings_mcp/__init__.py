"""SmartThings MCP Server package."""

import os
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv

    # Look for .env in current directory or parent directories
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try project root (where pyproject.toml is)
        load_dotenv()  # Searches parent directories automatically
except ImportError:
    # python-dotenv not installed, skip
    pass

from .server import SmartThingsMCPServer, main
from .client import SmartThingsClient

__version__ = "0.1.0"
__all__ = ["SmartThingsMCPServer", "SmartThingsClient", "main"]