"""
World backup management tools.

Provides tools for creating, listing, restoring, and deleting world backups.
"""

import subprocess
import json
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def ensure_backup_dir(backup_dir: str) -> bool:
    """Ensure the backup directory exists."""
    try:
        os.makedirs(backup_dir, exist_ok=True)
        return True
    except Exception:
        return False


def get_backup_files(backup_dir: str) -> list[dict]:
    """Get list of backup files with metadata."""
    backups = []
    if not os.path.exists(backup_dir):
        return backups

    for filename in os.listdir(backup_dir):
        if filename.endswith(".tar.gz"):
            filepath = os.path.join(backup_dir, filename)
            stat = os.stat(filepath)
            backups.append({
                "name": filename,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    # Sort by creation time, newest first
    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups


def register_backup_tools(mcp: FastMCP, config: dict):
    """Register backup management tools with the MCP server."""

    @mcp.tool()
    def backup_create(name: str = "") -> str:
        """
        Create a backup of the Valheim world saves.

        Args:
            name: Optional backup name. If empty, uses timestamp (e.g., backup_20240115_143022.tar.gz)

        Note: It's recommended to stop the server before creating a backup for consistency.
        """
        backup_dir = config["BACKUP_DIR"]
        data_dir = config["VALHEIM_DATA_DIR"]
        worlds_dir = os.path.join(data_dir, "worlds_local")

        # Check if worlds directory exists
        if not os.path.exists(worlds_dir):
            return json.dumps({
                "success": False,
                "message": f"Worlds directory not found: {worlds_dir}"
            })

        # Ensure backup directory exists
        if not ensure_backup_dir(backup_dir):
            return json.dumps({
                "success": False,
                "message": f"Could not create backup directory: {backup_dir}"
            })

        # Generate backup filename
        if name:
            # Sanitize name
            safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
            backup_name = f"{safe_name}.tar.gz"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}.tar.gz"

        backup_path = os.path.join(backup_dir, backup_name)

        # Check if backup already exists
        if os.path.exists(backup_path):
            return json.dumps({
                "success": False,
                "message": f"Backup already exists: {backup_name}"
            })

        try:
            # Create tarball of worlds directory
            run_command([
                "tar", "-czf", backup_path,
                "-C", data_dir,
                "worlds_local"
            ])

            # Get size of created backup
            size_mb = round(os.path.getsize(backup_path) / (1024 * 1024), 2)

            return json.dumps({
                "success": True,
                "message": "Backup created successfully",
                "backup_name": backup_name,
                "size_mb": size_mb,
                "path": backup_path
            })
        except subprocess.CalledProcessError as e:
            return json.dumps({
                "success": False,
                "message": f"Failed to create backup: {e.stderr}"
            })

    @mcp.tool()
    def backup_list() -> str:
        """
        List all available world backups.

        Returns backup names, sizes, and creation dates.
        """
        backup_dir = config["BACKUP_DIR"]
        backups = get_backup_files(backup_dir)

        return json.dumps({
            "success": True,
            "backup_dir": backup_dir,
            "backups": backups,
            "count": len(backups)
        }, indent=2)

    @mcp.tool()
    def backup_restore(name: str) -> str:
        """
        Restore a world backup.

        Args:
            name: The backup filename to restore (e.g., backup_20240115_143022.tar.gz)

        Warning: This will overwrite current world saves! The server should be stopped first.
        """
        backup_dir = config["BACKUP_DIR"]
        data_dir = config["VALHEIM_DATA_DIR"]
        backup_path = os.path.join(backup_dir, name)

        # Verify backup exists
        if not os.path.exists(backup_path):
            backups = get_backup_files(backup_dir)
            return json.dumps({
                "success": False,
                "message": f"Backup not found: {name}",
                "available_backups": [b["name"] for b in backups]
            })

        # Check if server is running
        result = run_command(["systemctl", "is-active", config["SERVICE_NAME"]], check=False)
        if result.stdout.strip() == "active":
            return json.dumps({
                "success": False,
                "message": "Server is running. Please stop the server before restoring a backup.",
                "hint": "Use server_stop first"
            })

        try:
            # Create a backup of current state before restoring
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = os.path.join(backup_dir, f"pre_restore_{timestamp}.tar.gz")

            worlds_dir = os.path.join(data_dir, "worlds_local")
            if os.path.exists(worlds_dir):
                run_command([
                    "tar", "-czf", pre_restore_backup,
                    "-C", data_dir,
                    "worlds_local"
                ])

            # Extract backup
            run_command([
                "tar", "-xzf", backup_path,
                "-C", data_dir
            ])

            return json.dumps({
                "success": True,
                "message": f"Backup restored successfully: {name}",
                "pre_restore_backup": os.path.basename(pre_restore_backup),
                "note": "You can now start the server"
            })
        except subprocess.CalledProcessError as e:
            return json.dumps({
                "success": False,
                "message": f"Failed to restore backup: {e.stderr}"
            })

    @mcp.tool()
    def backup_delete(name: str) -> str:
        """
        Delete a world backup.

        Args:
            name: The backup filename to delete (e.g., backup_20240115_143022.tar.gz)
        """
        backup_dir = config["BACKUP_DIR"]
        backup_path = os.path.join(backup_dir, name)

        # Verify backup exists
        if not os.path.exists(backup_path):
            backups = get_backup_files(backup_dir)
            return json.dumps({
                "success": False,
                "message": f"Backup not found: {name}",
                "available_backups": [b["name"] for b in backups]
            })

        try:
            os.remove(backup_path)
            return json.dumps({
                "success": True,
                "message": f"Backup deleted: {name}"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Failed to delete backup: {str(e)}"
            })
