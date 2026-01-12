"""Server status collector using systemctl and journalctl."""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..config import SERVICE_NAME, VALHEIM_DIR, LOG_PATTERNS


@dataclass
class ServerStatus:
    """Current server status information."""

    running: bool
    state: str  # "active", "inactive", "failed", "unknown"
    memory_mb: Optional[float] = None
    started_at: Optional[datetime] = None
    uptime_seconds: Optional[int] = None
    server_name: Optional[str] = None
    world_name: Optional[str] = None
    current_connections: int = 0


def get_server_status() -> ServerStatus:
    """Get current server status from systemd."""
    # Check if service is active
    try:
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=5,
        )
        state = result.stdout.strip()
        is_active = state == "active"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ServerStatus(running=False, state="unknown")

    status = ServerStatus(
        running=is_active,
        state=state,
    )

    if is_active:
        # Get detailed status
        try:
            show_result = subprocess.run(
                [
                    "systemctl",
                    "show",
                    SERVICE_NAME,
                    "--property=ActiveEnterTimestamp,MemoryCurrent",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in show_result.stdout.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key == "ActiveEnterTimestamp" and value:
                        try:
                            # Parse systemd timestamp format
                            # Example: "Sat 2026-01-11 20:00:00 EST"
                            status.started_at = _parse_systemd_timestamp(value)
                            if status.started_at:
                                delta = datetime.now() - status.started_at
                                status.uptime_seconds = int(delta.total_seconds())
                        except (ValueError, TypeError):
                            pass
                    elif key == "MemoryCurrent" and value:
                        try:
                            # Value is in bytes, convert to MB
                            mem_bytes = int(value)
                            if mem_bytes > 0:
                                status.memory_mb = mem_bytes / (1024 * 1024)
                        except ValueError:
                            pass

            # Get current connection count from logs
            status.current_connections = _get_current_connections()

            # Get server/world name from start script
            server_name, world_name = _get_server_info()
            status.server_name = server_name
            status.world_name = world_name

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return status


def _parse_systemd_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse systemd timestamp format."""
    # Format: "Sat 2026-01-11 20:00:00 EST"
    try:
        # Remove day name and timezone, parse the middle part
        parts = timestamp_str.split()
        if len(parts) >= 3:
            date_str = f"{parts[1]} {parts[2]}"
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        pass
    return None


def _get_current_connections() -> int:
    """Parse most recent 'Connections N' line from logs."""
    try:
        result = subprocess.run(
            ["journalctl", "-u", SERVICE_NAME, "-n", "50", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        pattern = re.compile(LOG_PATTERNS["connections"])
        matches = pattern.findall(result.stdout)
        return int(matches[-1]) if matches else 0

    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return 0


def _get_server_info() -> tuple[Optional[str], Optional[str]]:
    """Parse server name and world name from start_server.sh."""
    start_script = VALHEIM_DIR / "start_server.sh"
    server_name = None
    world_name = None

    try:
        if not start_script.exists():
            return server_name, world_name

        content = start_script.read_text()

        # Look for -name "ServerName"
        name_match = re.search(r'-name\s+"([^"]+)"', content)
        if name_match:
            server_name = name_match.group(1)

        # Look for -world "WorldName"
        world_match = re.search(r'-world\s+"([^"]+)"', content)
        if world_match:
            world_name = world_match.group(1)

    except (OSError, PermissionError):
        pass

    return server_name, world_name
