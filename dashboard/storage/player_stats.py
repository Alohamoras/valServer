"""TOML-based player statistics storage."""

import tomli
import tomli_w
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import PLAYER_STATS_FILE


@dataclass
class PlayerStats:
    """Statistics for a single player."""

    name: str
    first_seen: str  # ISO format
    last_seen: str   # ISO format
    total_playtime_seconds: int
    session_count: int

    @property
    def first_seen_dt(self) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(self.first_seen)
        except ValueError:
            return None

    @property
    def last_seen_dt(self) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(self.last_seen)
        except ValueError:
            return None


class PlayerStatsStorage:
    """Manages persistent player statistics in TOML format."""

    def __init__(self, stats_file: Path = PLAYER_STATS_FILE):
        self.stats_file = stats_file
        self.data: dict = {"metadata": {}, "players": {}}

    def load(self) -> bool:
        """
        Load stats from TOML file.

        Returns True if loaded successfully, False if file doesn't exist
        or is corrupted (in which case a backup is created).
        """
        if not self.stats_file.exists():
            # Initialize with empty data
            self._initialize_empty()
            return False

        try:
            with open(self.stats_file, "rb") as f:
                self.data = tomli.load(f)

            # Ensure required keys exist
            if "metadata" not in self.data:
                self.data["metadata"] = {}
            if "players" not in self.data:
                self.data["players"] = {}

            return True

        except tomli.TOMLDecodeError:
            # Backup corrupt file and start fresh
            backup_path = self.stats_file.with_suffix(".toml.bak")
            try:
                self.stats_file.rename(backup_path)
            except OSError:
                pass

            self._initialize_empty()
            return False

        except (OSError, PermissionError):
            self._initialize_empty()
            return False

    def _initialize_empty(self):
        """Initialize with empty data structure."""
        self.data = {
            "metadata": {
                "version": 1,
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            },
            "players": {},
        }

    def save(self) -> bool:
        """
        Save stats to TOML file.

        Returns True if saved successfully, False otherwise.
        """
        try:
            # Ensure parent directory exists
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)

            # Update metadata
            self.data["metadata"]["last_updated"] = datetime.now().isoformat()
            self.data["metadata"]["version"] = 1

            with open(self.stats_file, "wb") as f:
                tomli_w.dump(self.data, f)

            return True

        except (OSError, PermissionError):
            return False

    def get_player(self, steam_id: str) -> Optional[PlayerStats]:
        """Get stats for a specific player by Steam ID."""
        if steam_id in self.data.get("players", {}):
            player_data = self.data["players"][steam_id]
            return PlayerStats(
                name=player_data.get("name", "Unknown"),
                first_seen=player_data.get("first_seen", ""),
                last_seen=player_data.get("last_seen", ""),
                total_playtime_seconds=player_data.get("total_playtime_seconds", 0),
                session_count=player_data.get("session_count", 0),
            )
        return None

    def update_player_session(
        self,
        steam_id: str,
        player_name: str,
        session_duration_seconds: int,
        connect_time: datetime,
    ):
        """
        Update player stats with a completed session.

        Args:
            steam_id: Player's Steam ID
            player_name: Player's character name
            session_duration_seconds: Duration of the session in seconds
            connect_time: When the session started
        """
        now = datetime.now().isoformat()

        if steam_id not in self.data.setdefault("players", {}):
            self.data["players"][steam_id] = {
                "name": player_name,
                "first_seen": connect_time.isoformat(),
                "last_seen": now,
                "total_playtime_seconds": 0,
                "session_count": 0,
            }

        player = self.data["players"][steam_id]
        player["name"] = player_name  # Update in case of name change
        player["last_seen"] = now
        player["total_playtime_seconds"] = (
            player.get("total_playtime_seconds", 0) + session_duration_seconds
        )
        player["session_count"] = player.get("session_count", 0) + 1

    def get_all_players(self) -> dict[str, PlayerStats]:
        """Get stats for all players."""
        result = {}
        for steam_id, data in self.data.get("players", {}).items():
            result[steam_id] = PlayerStats(
                name=data.get("name", "Unknown"),
                first_seen=data.get("first_seen", ""),
                last_seen=data.get("last_seen", ""),
                total_playtime_seconds=data.get("total_playtime_seconds", 0),
                session_count=data.get("session_count", 0),
            )
        return result

    def get_players_sorted_by_playtime(self) -> list[tuple[str, PlayerStats]]:
        """Get all players sorted by total playtime (descending)."""
        players = self.get_all_players()
        return sorted(
            players.items(),
            key=lambda x: x[1].total_playtime_seconds,
            reverse=True,
        )
