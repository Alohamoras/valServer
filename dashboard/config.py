"""Configuration constants for the Valheim Server Dashboard."""

import os
from dataclasses import dataclass
from pathlib import Path


# File paths
STEAM_USER = "steam"
STEAM_HOME = Path("/home/steam")
VALHEIM_DIR = STEAM_HOME / "valheim-server"
VALHEIM_DATA_DIR = STEAM_HOME / ".config/unity3d/IronGate/Valheim"
SERVICE_NAME = "valheim"


def _get_stats_file_path() -> Path:
    """
    Determine the best location for the player stats file.

    Priority:
    1. VALHEIM_STATS_FILE environment variable
    2. /home/steam/valheim-player-stats.toml (if writable)
    3. ~/.local/share/valheim-dashboard/player-stats.toml (fallback)
    """
    # Check environment variable first
    env_path = os.environ.get("VALHEIM_STATS_FILE")
    if env_path:
        return Path(env_path)

    # Try steam home if accessible
    steam_path = STEAM_HOME / "valheim-player-stats.toml"
    try:
        if STEAM_HOME.exists():
            # Check if we can write to steam home
            if os.access(STEAM_HOME, os.W_OK):
                return steam_path
    except (OSError, PermissionError):
        pass

    # Fallback to user's local data directory
    local_dir = Path.home() / ".local" / "share" / "valheim-dashboard"
    return local_dir / "player-stats.toml"


PLAYER_STATS_FILE = _get_stats_file_path()


@dataclass
class RefreshConfig:
    """Configuration for component refresh intervals (in seconds)."""

    display: float = 1.0          # Re-render display every second
    system_stats: float = 2.0     # System stats every 2 seconds
    server_status: float = 5.0    # Check status every 5 seconds
    logs: float = 5.0             # Logs every 5 seconds
    player_tracking: float = 10.0 # Online players every 10 seconds
    player_stats: float = 60.0    # Historical stats every minute


# Log parsing patterns
LOG_PATTERNS = {
    "connections": r"Connections (\d+) ZDOS:",
    "handshake": r"Got handshake from client (\d+)",
    "character": r"Got character ZDOID from (.+?) :",
    "disconnect": r"Closing socket (\d+)",
    "world_saved": r"World saved \( ([\d.]+)ms \)",
}

# Noise patterns to filter from log display
LOG_NOISE_PATTERNS = [
    "Unloading unused assets",
    "Unloading 0 Unused",
    "FindLiveObjects",
    "CreateObjectMapping",
    "MarkObjects",
    "DeleteObjects",
]
