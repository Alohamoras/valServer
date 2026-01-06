#!/usr/bin/env python3
"""
Valheim Dedicated Server MCP Server

Provides Claude with tools to manage a Valheim dedicated server.
"""

from mcp.server.fastmcp import FastMCP

from tools.server import register_server_tools
from tools.config import register_config_tools
from tools.backup import register_backup_tools
from tools.update import register_update_tools

# Configuration paths
CONFIG = {
    "STEAM_USER": "steam",
    "STEAM_HOME": "/home/steam",
    "STEAMCMD_DIR": "/home/steam/steamcmd",
    "VALHEIM_DIR": "/home/steam/valheim-server",
    "VALHEIM_DATA_DIR": "/home/steam/.config/unity3d/IronGate/Valheim",
    "VALHEIM_PLUS_CONFIG": "/home/steam/valheim-server/BepInEx/config/valheim_plus.cfg",
    "BACKUP_DIR": "/home/steam/valheim-backups",
    "SERVICE_NAME": "valheim",
}

mcp = FastMCP("valheim-server")

# Register all tools
register_server_tools(mcp, CONFIG)
register_config_tools(mcp, CONFIG)
register_backup_tools(mcp, CONFIG)
register_update_tools(mcp, CONFIG)


if __name__ == "__main__":
    mcp.run()
