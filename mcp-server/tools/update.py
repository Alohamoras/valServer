"""
Server and mod update tools.

Provides tools for updating Valheim Dedicated Server and Valheim Plus.
"""

import subprocess
import json
import os
import tempfile
import re
from mcp.server import Server
from mcp.types import Tool, TextContent


VALHEIM_PLUS_RELEASES_URL = "https://api.github.com/repos/Grantapher/ValheimPlus/releases/latest"
VALHEIM_PLUS_DOWNLOAD_URL = "https://github.com/Grantapher/ValheimPlus/releases/latest/download/UnixServer.tar.gz"


def run_command(cmd: list[str], check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout)


def get_service_status(service_name: str) -> bool:
    """Check if a systemd service is running."""
    result = run_command(["systemctl", "is-active", service_name], check=False)
    return result.stdout.strip() == "active"


def get_installed_valheimplus_version(valheim_dir: str) -> str | None:
    """Try to determine installed Valheim Plus version."""
    # Check changelog or version file
    changelog_path = os.path.join(valheim_dir, "BepInEx", "plugins", "ValheimPlus", "changelog.txt")
    if os.path.exists(changelog_path):
        try:
            with open(changelog_path, "r") as f:
                first_line = f.readline()
                # Version usually in format "Version X.X.X"
                match = re.search(r"(\d+\.\d+\.\d+)", first_line)
                if match:
                    return match.group(1)
        except Exception:
            pass

    # Alternative: check BepInEx log
    return None


def get_latest_valheimplus_version() -> str | None:
    """Get the latest Valheim Plus version from GitHub."""
    try:
        result = run_command(["curl", "-s", VALHEIM_PLUS_RELEASES_URL], check=False)
        if result.returncode == 0:
            # Parse JSON response
            import json
            data = json.loads(result.stdout)
            tag = data.get("tag_name", "")
            # Remove 'v' prefix if present
            return tag.lstrip("v") if tag else None
    except Exception:
        pass
    return None


def register_update_tools(server: Server, config: dict):
    """Register update management tools with the MCP server."""

    @server.tool()
    async def update_check() -> list[TextContent]:
        """
        Check for available updates to Valheim and Valheim Plus.

        Compares installed versions with latest available versions.
        """
        result = {
            "valheim": {
                "status": "unknown",
                "message": "SteamCMD check not implemented - use update_server to update"
            },
            "valheim_plus": {}
        }

        # Check Valheim Plus version
        installed_vp = get_installed_valheimplus_version(config["VALHEIM_DIR"])
        latest_vp = get_latest_valheimplus_version()

        result["valheim_plus"]["installed_version"] = installed_vp or "unknown"
        result["valheim_plus"]["latest_version"] = latest_vp or "unknown"

        if installed_vp and latest_vp:
            if installed_vp == latest_vp:
                result["valheim_plus"]["status"] = "up_to_date"
            else:
                result["valheim_plus"]["status"] = "update_available"
        else:
            result["valheim_plus"]["status"] = "unknown"

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    @server.tool()
    async def update_server() -> list[TextContent]:
        """
        Update the Valheim Dedicated Server via SteamCMD.

        Warning: The server will be stopped during the update process.
        """
        service_name = config["SERVICE_NAME"]
        was_running = get_service_status(service_name)

        # Stop server if running
        if was_running:
            try:
                run_command(["sudo", "systemctl", "stop", service_name])
            except subprocess.CalledProcessError as e:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "message": f"Failed to stop server: {e.stderr}"
                }))]

        # Run SteamCMD update
        try:
            steamcmd = os.path.join(config["STEAMCMD_DIR"], "steamcmd.sh")
            run_command([
                steamcmd,
                "+force_install_dir", config["VALHEIM_DIR"],
                "+login", "anonymous",
                "+app_update", "896660", "validate",
                "+quit"
            ], timeout=600)  # 10 minute timeout for download

            result = {
                "success": True,
                "message": "Valheim server updated successfully"
            }

            # Restart server if it was running
            if was_running:
                run_command(["sudo", "systemctl", "start", service_name])
                result["server_restarted"] = True

            return [TextContent(type="text", text=json.dumps(result))]
        except subprocess.TimeoutExpired:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": "Update timed out after 10 minutes"
            }))]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Update failed: {e.stderr}"
            }))]

    @server.tool()
    async def update_valheimplus() -> list[TextContent]:
        """
        Update Valheim Plus to the latest version.

        Warning: The server will be stopped during the update process.
        """
        service_name = config["SERVICE_NAME"]
        was_running = get_service_status(service_name)

        # Stop server if running
        if was_running:
            try:
                run_command(["sudo", "systemctl", "stop", service_name])
            except subprocess.CalledProcessError as e:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "message": f"Failed to stop server: {e.stderr}"
                }))]

        try:
            # Download and extract Valheim Plus
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "valheimplus.tar.gz")

                # Download
                run_command([
                    "wget", "-q", "-O", archive_path,
                    VALHEIM_PLUS_DOWNLOAD_URL
                ], timeout=120)

                # Extract
                run_command([
                    "tar", "-xzf", archive_path,
                    "-C", config["VALHEIM_DIR"]
                ])

                # Download config file
                latest_version = get_latest_valheimplus_version()
                if latest_version:
                    config_url = f"https://github.com/Grantapher/ValheimPlus/releases/download/{latest_version}/valheim_plus.cfg"
                    config_path = config["VALHEIM_PLUS_CONFIG"]
                    run_command([
                        "wget", "-q", "-O", config_path,
                        config_url
                    ], check=False)  # Don't fail if config download fails

            result = {
                "success": True,
                "message": "Valheim Plus updated successfully",
                "version": latest_version or "unknown"
            }

            # Restart server if it was running
            if was_running:
                run_command(["sudo", "systemctl", "start", service_name])
                result["server_restarted"] = True

            return [TextContent(type="text", text=json.dumps(result))]
        except subprocess.TimeoutExpired:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": "Download timed out"
            }))]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "message": f"Update failed: {e.stderr}"
            }))]

    @server.tool()
    async def update_all() -> list[TextContent]:
        """
        Update both Valheim server and Valheim Plus.

        Stops the server, updates both components, then restarts if it was running.
        """
        service_name = config["SERVICE_NAME"]
        was_running = get_service_status(service_name)
        results = {"valheim": {}, "valheim_plus": {}}

        # Stop server if running
        if was_running:
            try:
                run_command(["sudo", "systemctl", "stop", service_name])
            except subprocess.CalledProcessError as e:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "message": f"Failed to stop server: {e.stderr}"
                }))]

        # Update Valheim
        try:
            steamcmd = os.path.join(config["STEAMCMD_DIR"], "steamcmd.sh")
            run_command([
                steamcmd,
                "+force_install_dir", config["VALHEIM_DIR"],
                "+login", "anonymous",
                "+app_update", "896660", "validate",
                "+quit"
            ], timeout=600)
            results["valheim"] = {"success": True, "message": "Updated successfully"}
        except Exception as e:
            results["valheim"] = {"success": False, "message": str(e)}

        # Update Valheim Plus
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = os.path.join(temp_dir, "valheimplus.tar.gz")

                run_command([
                    "wget", "-q", "-O", archive_path,
                    VALHEIM_PLUS_DOWNLOAD_URL
                ], timeout=120)

                run_command([
                    "tar", "-xzf", archive_path,
                    "-C", config["VALHEIM_DIR"]
                ])

                # Download config
                latest_version = get_latest_valheimplus_version()
                if latest_version:
                    config_url = f"https://github.com/Grantapher/ValheimPlus/releases/download/{latest_version}/valheim_plus.cfg"
                    run_command([
                        "wget", "-q", "-O", config["VALHEIM_PLUS_CONFIG"],
                        config_url
                    ], check=False)

            results["valheim_plus"] = {
                "success": True,
                "message": "Updated successfully",
                "version": latest_version or "unknown"
            }
        except Exception as e:
            results["valheim_plus"] = {"success": False, "message": str(e)}

        # Restart server if it was running
        if was_running:
            try:
                run_command(["sudo", "systemctl", "start", service_name])
                results["server_restarted"] = True
            except Exception as e:
                results["server_restart_error"] = str(e)

        overall_success = results["valheim"].get("success", False) and results["valheim_plus"].get("success", False)
        results["success"] = overall_success

        return [TextContent(type="text", text=json.dumps(results, indent=2))]
