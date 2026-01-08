"""
Mod management tools using Valheim Mod Manager (vmm).

Provides tools for listing, adding, removing, searching, and updating mods.
"""

import subprocess
import json
import os
import re
from mcp.server.fastmcp import FastMCP


def run_command(cmd: list[str], check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout)


def run_vmm_command(steam_home: str, args: list[str], check: bool = False, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a vmm command as the steam user."""
    # vmm needs to be run from the directory containing vmm_config.toml
    # and needs cargo in PATH
    cmd = [
        "sudo", "-u", "steam", "-i", "bash", "-c",
        f"cd {steam_home} && source {steam_home}/.cargo/env && vmm {' '.join(args)}"
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout)


def read_vmm_config(config_path: str) -> dict | None:
    """Read and parse the vmm_config.toml file."""
    if not os.path.exists(config_path):
        return None

    config = {
        "mod_list": [],
        "log_level": "info",
        "cache_dir": "",
        "install_dir": ""
    }

    try:
        with open(config_path, "r") as f:
            content = f.read()

        # Parse mod_list
        mod_list_match = re.search(r'mod_list\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if mod_list_match:
            mods_str = mod_list_match.group(1)
            mods = re.findall(r'"([^"]+)"', mods_str)
            config["mod_list"] = mods

        # Parse other fields
        for field in ["log_level", "cache_dir", "install_dir"]:
            match = re.search(rf'{field}\s*=\s*"([^"]*)"', content)
            if match:
                config[field] = match.group(1)

        return config
    except Exception:
        return None


def write_vmm_config(config_path: str, config: dict) -> bool:
    """Write the vmm_config.toml file."""
    try:
        # Format mod_list
        mod_list_str = ", ".join(f'"{mod}"' for mod in config["mod_list"])

        content = f'''mod_list = [{mod_list_str}]
log_level = "{config.get('log_level', 'info')}"
cache_dir = "{config.get('cache_dir', '')}"
install_dir = "{config.get('install_dir', '')}"
'''
        with open(config_path, "w") as f:
            f.write(content)

        # Ensure steam user owns the file
        run_command(["chown", "steam:steam", config_path], check=False)
        return True
    except Exception:
        return False


def register_mods_tools(mcp: FastMCP, config: dict):
    """Register mod management tools with the MCP server."""

    vmm_config_path = os.path.join(config["STEAM_HOME"], "vmm_config.toml")

    @mcp.tool()
    def mods_list() -> str:
        """
        List all configured mods from vmm_config.toml.

        Shows the mods that are configured to be installed/updated by vmm.
        """
        vmm_config = read_vmm_config(vmm_config_path)

        if vmm_config is None:
            return json.dumps({
                "success": False,
                "message": f"Could not read vmm config at {vmm_config_path}"
            })

        return json.dumps({
            "success": True,
            "mods": vmm_config["mod_list"],
            "count": len(vmm_config["mod_list"]),
            "install_dir": vmm_config["install_dir"],
            "config_path": vmm_config_path
        }, indent=2)

    @mcp.tool()
    def mods_add(mod_name: str, install: bool = True) -> str:
        """
        Add a mod to the configuration.

        Args:
            mod_name: The mod to add in "Owner-ModName" format (e.g., "ValheimModding-Jotunn")
            install: If True, also run vmm update to install the mod immediately

        Use mods_search to find the correct mod name first.
        """
        vmm_config = read_vmm_config(vmm_config_path)

        if vmm_config is None:
            return json.dumps({
                "success": False,
                "message": f"Could not read vmm config at {vmm_config_path}"
            })

        # Check if mod already exists
        if mod_name in vmm_config["mod_list"]:
            return json.dumps({
                "success": False,
                "message": f"Mod already configured: {mod_name}"
            })

        # Add the mod
        vmm_config["mod_list"].append(mod_name)

        if not write_vmm_config(vmm_config_path, vmm_config):
            return json.dumps({
                "success": False,
                "message": "Failed to write vmm config"
            })

        result = {
            "success": True,
            "message": f"Added mod: {mod_name}",
            "mods": vmm_config["mod_list"]
        }

        # Optionally install the mod
        if install:
            try:
                # Update manifest first
                run_vmm_command(config["STEAM_HOME"], ["update", "manifest"], timeout=120)
                # Then update mods
                update_result = run_vmm_command(config["STEAM_HOME"], ["update", "mods"], timeout=300)
                result["installed"] = True
                result["install_output"] = update_result.stdout + update_result.stderr
            except subprocess.TimeoutExpired:
                result["installed"] = False
                result["install_error"] = "Installation timed out"
            except Exception as e:
                result["installed"] = False
                result["install_error"] = str(e)

        return json.dumps(result, indent=2)

    @mcp.tool()
    def mods_remove(mod_name: str) -> str:
        """
        Remove a mod from the configuration.

        Args:
            mod_name: The mod to remove in "Owner-ModName" format

        Note: This only removes from config. To fully uninstall, manually delete
        the mod files from BepInEx/plugins.
        """
        vmm_config = read_vmm_config(vmm_config_path)

        if vmm_config is None:
            return json.dumps({
                "success": False,
                "message": f"Could not read vmm config at {vmm_config_path}"
            })

        # Check if mod exists
        if mod_name not in vmm_config["mod_list"]:
            return json.dumps({
                "success": False,
                "message": f"Mod not found in config: {mod_name}",
                "configured_mods": vmm_config["mod_list"]
            })

        # Prevent removing core mods
        core_mods = ["denikson-BepInExPack_Valheim"]
        if mod_name in core_mods:
            return json.dumps({
                "success": False,
                "message": f"Cannot remove core mod: {mod_name}",
                "hint": "BepInEx is required for all other mods to work"
            })

        # Remove the mod
        vmm_config["mod_list"].remove(mod_name)

        if not write_vmm_config(vmm_config_path, vmm_config):
            return json.dumps({
                "success": False,
                "message": "Failed to write vmm config"
            })

        return json.dumps({
            "success": True,
            "message": f"Removed mod from config: {mod_name}",
            "mods": vmm_config["mod_list"],
            "note": "Mod files may still exist in BepInEx/plugins - delete manually if needed"
        }, indent=2)

    @mcp.tool()
    def mods_search(query: str) -> str:
        """
        Search for mods on Thunderstore.

        Args:
            query: Search term (case-insensitive)

        Returns matching mods with owner, name, version, and description.
        """
        try:
            result = run_vmm_command(config["STEAM_HOME"], ["search", query], timeout=60)

            # Parse the output
            output = result.stdout + result.stderr

            return json.dumps({
                "success": True,
                "query": query,
                "results": output.strip(),
                "hint": "Use mods_add with the 'Owner-ModName' format to add a mod"
            }, indent=2)
        except subprocess.TimeoutExpired:
            return json.dumps({
                "success": False,
                "message": "Search timed out"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Search failed: {str(e)}"
            })

    @mcp.tool()
    def mods_update() -> str:
        """
        Update all configured mods to their latest versions.

        Fetches the latest mod manifest from Thunderstore and updates all mods.
        The server should be stopped before updating mods.
        """
        # Check if server is running
        result = run_command(["systemctl", "is-active", config["SERVICE_NAME"]], check=False)
        server_running = result.stdout.strip() == "active"

        if server_running:
            return json.dumps({
                "success": False,
                "message": "Server is running. Please stop the server before updating mods.",
                "hint": "Use server_stop first"
            })

        try:
            # Update manifest
            manifest_result = run_vmm_command(config["STEAM_HOME"], ["update", "manifest"], timeout=120)
            manifest_output = manifest_result.stdout + manifest_result.stderr

            # Update mods
            mods_result = run_vmm_command(config["STEAM_HOME"], ["update", "mods"], timeout=300)
            mods_output = mods_result.stdout + mods_result.stderr

            return json.dumps({
                "success": True,
                "message": "Mods updated successfully",
                "manifest_update": manifest_output.strip(),
                "mods_update": mods_output.strip()
            }, indent=2)
        except subprocess.TimeoutExpired:
            return json.dumps({
                "success": False,
                "message": "Update timed out"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Update failed: {str(e)}"
            })
