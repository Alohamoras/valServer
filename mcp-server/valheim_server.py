#!/usr/bin/env python3
"""
Valheim Dedicated Server MCP Server

Provides Claude with tools to manage a Valheim dedicated server.
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

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

server = Server("valheim-server")


def register_all_tools():
    """Register all tool modules with the MCP server."""
    register_server_tools(server, CONFIG)
    register_config_tools(server, CONFIG)
    register_backup_tools(server, CONFIG)
    register_update_tools(server, CONFIG)


async def main():
    """Run the MCP server."""
    register_all_tools()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
