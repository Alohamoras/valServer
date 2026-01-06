"""
Server lifecycle management tools.

Provides tools for starting, stopping, restarting, and monitoring the Valheim server.
"""

import subprocess
import json
import re
from datetime import datetime
from mcp.server import Server
from mcp.types import Tool, TextContent


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def get_service_status(service_name: str) -> dict:
    """Get detailed status of a systemd service."""
    result = run_command(["systemctl", "is-active", service_name], check=False)
    is_active = result.stdout.strip() == "active"

    status = {
        "running": is_active,
        "state": result.stdout.strip(),
    }

    if is_active:
        # Get uptime and memory usage
        show_result = run_command(
            ["systemctl", "show", service_name, "--property=ActiveEnterTimestamp,MemoryCurrent"],
            check=False
        )
        for line in show_result.stdout.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                if key == "ActiveEnterTimestamp" and value:
                    status["started_at"] = value
                elif key == "MemoryCurrent" and value and value != "[not set]":
                    try:
                        mem_bytes = int(value)
                        status["memory_mb"] = round(mem_bytes / (1024 * 1024), 1)
                    except ValueError:
                        pass

    return status


def get_player_count_from_logs(lines: int = 100) -> int | None:
    """Try to parse player count from recent logs."""
    try:
        result = run_command(
            ["journalctl", "-u", "valheim", "-n", str(lines), "--no-pager"],
            check=False
        )
        # Look for connection/disconnection patterns
        connections = len(re.findall(r"Got character ZDOID", result.stdout))
        disconnections = len(re.findall(r"Closing socket", result.stdout))
        # This is a rough estimate
        return max(0, connections - disconnections)
    except Exception:
        return None


def register_server_tools(server: Server, config: dict):
    """Register server management tools with the MCP server."""

    @server.tool()
    async def server_status() -> list[TextContent]:
        """
        Get the current status of the Valheim server.

        Returns running state, uptime, memory usage, and estimated player count.
        """
        status = get_service_status(config["SERVICE_NAME"])

        # Try to get player count if server is running
        if status["running"]:
            player_count = get_player_count_from_logs()
            if player_count is not None:
                status["estimated_players"] = player_count

        return [TextContent(type="text", text=json.dumps(status, indent=2))]

    @server.tool()
    async def server_start() -> list[TextContent]:
        """
        Start the Valheim server.

        Uses systemctl to start the valheim service.
        """
        # Check if already running
        status = get_service_status(config["SERVICE_NAME"])
        if status["running"]:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": "Server is already running"
            }))]

        try:
            run_command(["sudo", "systemctl", "start", config["SERVICE_NAME"]])
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "message": "Server started successfully"
            }))]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Failed to start server: {e.stderr}"
            }))]

    @server.tool()
    async def server_stop(graceful: bool = True) -> list[TextContent]:
        """
        Stop the Valheim server.

        Args:
            graceful: If true, sends SIGINT to allow graceful shutdown with save.
                     If false, stops immediately.
        """
        status = get_service_status(config["SERVICE_NAME"])
        if not status["running"]:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": "Server is not running"
            }))]

        try:
            run_command(["sudo", "systemctl", "stop", config["SERVICE_NAME"]])
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "message": "Server stopped successfully"
            }))]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Failed to stop server: {e.stderr}"
            }))]

    @server.tool()
    async def server_restart() -> list[TextContent]:
        """
        Restart the Valheim server.

        Gracefully stops the server (allowing it to save) then starts it again.
        """
        try:
            run_command(["sudo", "systemctl", "restart", config["SERVICE_NAME"]])
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "message": "Server restarted successfully"
            }))]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Failed to restart server: {e.stderr}"
            }))]

    @server.tool()
    async def server_logs(lines: int = 50, filter: str = "") -> list[TextContent]:
        """
        Get recent server logs.

        Args:
            lines: Number of log lines to retrieve (default 50, max 500)
            filter: Optional string to filter logs (grep pattern)
        """
        lines = min(max(1, lines), 500)  # Clamp between 1 and 500

        try:
            cmd = ["journalctl", "-u", config["SERVICE_NAME"], "-n", str(lines), "--no-pager"]
            result = run_command(cmd, check=False)

            output = result.stdout

            # Apply filter if provided
            if filter:
                filtered_lines = [line for line in output.split("\n") if filter.lower() in line.lower()]
                output = "\n".join(filtered_lines)

            return [TextContent(type="text", text=output if output else "No logs found")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error retrieving logs: {str(e)}")]

    @server.tool()
    async def server_info() -> list[TextContent]:
        """
        Get server configuration information.

        Returns server name, world name, ports, and file paths.
        """
        info = {
            "paths": {
                "server_dir": config["VALHEIM_DIR"],
                "data_dir": config["VALHEIM_DATA_DIR"],
                "config_file": config["VALHEIM_PLUS_CONFIG"],
                "backup_dir": config["BACKUP_DIR"],
            },
            "ports": {
                "game": "2456-2458 UDP",
            },
            "service": config["SERVICE_NAME"],
        }

        # Try to read server name and world from start script
        start_script = f"{config['VALHEIM_DIR']}/start_server.sh"
        try:
            with open(start_script, "r") as f:
                content = f.read()

            # Parse -name and -world from the script
            name_match = re.search(r'-name\s+"([^"]+)"', content)
            world_match = re.search(r'-world\s+"([^"]+)"', content)

            if name_match:
                info["server_name"] = name_match.group(1)
            if world_match:
                info["world_name"] = world_match.group(1)
        except FileNotFoundError:
            info["warning"] = "Server may not be installed (start_server.sh not found)"
        except Exception as e:
            info["warning"] = f"Could not read server config: {str(e)}"

        return [TextContent(type="text", text=json.dumps(info, indent=2))]
