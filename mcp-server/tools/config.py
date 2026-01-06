"""
Valheim Plus configuration management tools.

Provides tools for reading and modifying Valheim Plus configuration.
"""

import json
import configparser
import os
from mcp.server import Server
from mcp.types import Tool, TextContent


class ValheimPlusConfig:
    """Parser for Valheim Plus configuration files."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.parser = configparser.ConfigParser()
        # Preserve case of keys
        self.parser.optionxform = str

    def load(self) -> bool:
        """Load the configuration file."""
        if not os.path.exists(self.config_path):
            return False
        self.parser.read(self.config_path)
        return True

    def save(self):
        """Save the configuration file."""
        with open(self.config_path, "w") as f:
            self.parser.write(f)

    def get_sections(self) -> list[str]:
        """Get all section names."""
        return self.parser.sections()

    def get_section(self, section: str) -> dict | None:
        """Get all key-value pairs in a section."""
        if section not in self.parser:
            return None
        return dict(self.parser[section])

    def get_all(self) -> dict:
        """Get entire configuration as a dictionary."""
        result = {}
        for section in self.parser.sections():
            result[section] = dict(self.parser[section])
        return result

    def set_value(self, section: str, key: str, value: str) -> bool:
        """Set a configuration value."""
        if section not in self.parser:
            return False
        self.parser[section][key] = value
        return True

    def get_value(self, section: str, key: str) -> str | None:
        """Get a specific configuration value."""
        if section not in self.parser:
            return None
        return self.parser[section].get(key)


def register_config_tools(server: Server, config: dict):
    """Register configuration management tools with the MCP server."""

    @server.tool()
    async def config_get(section: str = "") -> list[TextContent]:
        """
        Get Valheim Plus configuration values.

        Args:
            section: Optional section name. If empty, returns all sections.
                    Example sections: Server, Map, Player, Building, etc.
        """
        vp_config = ValheimPlusConfig(config["VALHEIM_PLUS_CONFIG"])

        if not vp_config.load():
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Config file not found: {config['VALHEIM_PLUS_CONFIG']}"
            }))]

        if section:
            section_data = vp_config.get_section(section)
            if section_data is None:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "message": f"Section '{section}' not found",
                    "available_sections": vp_config.get_sections()
                }))]
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "section": section,
                "values": section_data
            }, indent=2))]
        else:
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "config": vp_config.get_all()
            }, indent=2))]

    @server.tool()
    async def config_set(section: str, key: str, value: str) -> list[TextContent]:
        """
        Set a Valheim Plus configuration value.

        Args:
            section: The config section (e.g., "Server", "Player", "Building")
            key: The configuration key (e.g., "enabled", "maxPlayers")
            value: The value to set

        Note: Server restart required for changes to take effect.
        """
        vp_config = ValheimPlusConfig(config["VALHEIM_PLUS_CONFIG"])

        if not vp_config.load():
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Config file not found: {config['VALHEIM_PLUS_CONFIG']}"
            }))]

        # Get old value for confirmation
        old_value = vp_config.get_value(section, key)

        if not vp_config.set_value(section, key, value):
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Section '{section}' not found",
                "available_sections": vp_config.get_sections()
            }))]

        try:
            vp_config.save()
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "message": f"Updated [{section}] {key}",
                "old_value": old_value,
                "new_value": value,
                "note": "Restart the server for changes to take effect"
            }))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Failed to save config: {str(e)}"
            }))]

    @server.tool()
    async def config_sections() -> list[TextContent]:
        """
        List all available configuration sections in Valheim Plus.

        Returns a list of section names that can be used with config_get and config_set.
        """
        vp_config = ValheimPlusConfig(config["VALHEIM_PLUS_CONFIG"])

        if not vp_config.load():
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Config file not found: {config['VALHEIM_PLUS_CONFIG']}"
            }))]

        sections = vp_config.get_sections()
        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "sections": sections,
            "count": len(sections)
        }, indent=2))]
