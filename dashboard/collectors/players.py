"""Player session tracking from server logs."""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..config import SERVICE_NAME, LOG_PATTERNS


@dataclass
class PlayerSession:
    """A completed player session."""

    player_name: str
    steam_id: str
    connect_time: datetime
    disconnect_time: datetime

    @property
    def duration_seconds(self) -> int:
        return int((self.disconnect_time - self.connect_time).total_seconds())


@dataclass
class OnlinePlayer:
    """A currently online player."""

    name: str
    steam_id: str
    session_start: datetime

    @property
    def session_duration_seconds(self) -> int:
        return int((datetime.now() - self.session_start).total_seconds())


@dataclass
class PendingConnection:
    """A handshake waiting for character ZDOID."""

    steam_id: str
    handshake_time: datetime


@dataclass
class ActiveSession:
    """A fully connected player."""

    steam_id: str
    player_name: str
    connect_time: datetime


class SessionTracker:
    """
    State machine for tracking player sessions from log events.

    Flow:
    1. handshake -> pending connection (awaiting character)
    2. character ZDOID -> active session (player fully connected)
    3. closing socket -> session complete (calculate duration)
    """

    def __init__(self):
        self.pending: dict[str, PendingConnection] = {}
        self.active: dict[str, ActiveSession] = {}
        self.completed_sessions: list[PlayerSession] = []
        self.steam_to_name: dict[str, str] = {}
        self._last_processed_line: Optional[str] = None

    def process_handshake(self, steam_id: str, timestamp: datetime):
        """Player initiated connection."""
        self.pending[steam_id] = PendingConnection(steam_id, timestamp)

    def process_character_zdoid(self, player_name: str, timestamp: datetime):
        """
        Player fully loaded with character.

        Note: ZDOID event doesn't include Steam ID directly.
        Match to the most recent pending connection.
        """
        if not self.pending:
            return

        # Find the most recent pending connection by timestamp
        # (usually there's only one at a time)
        recent_pending = None
        recent_steam_id = None

        for steam_id, pending in self.pending.items():
            if recent_pending is None or pending.handshake_time > recent_pending.handshake_time:
                recent_pending = pending
                recent_steam_id = steam_id

        if recent_steam_id and recent_pending:
            del self.pending[recent_steam_id]

            self.active[recent_steam_id] = ActiveSession(
                steam_id=recent_steam_id,
                player_name=player_name,
                connect_time=recent_pending.handshake_time,
            )
            self.steam_to_name[recent_steam_id] = player_name

    def process_disconnect(self, steam_id: str, timestamp: datetime):
        """Player disconnected."""
        if steam_id in self.active:
            session = self.active.pop(steam_id)
            completed = PlayerSession(
                player_name=session.player_name,
                steam_id=steam_id,
                connect_time=session.connect_time,
                disconnect_time=timestamp,
            )
            self.completed_sessions.append(completed)

        # Also clear any pending connection
        self.pending.pop(steam_id, None)

    def get_online_players(self) -> list[OnlinePlayer]:
        """Return list of currently connected players."""
        return [
            OnlinePlayer(
                name=session.player_name,
                steam_id=session.steam_id,
                session_start=session.connect_time,
            )
            for session in self.active.values()
        ]

    def get_and_clear_completed_sessions(self) -> list[PlayerSession]:
        """Get completed sessions and clear the list."""
        sessions = self.completed_sessions[:]
        self.completed_sessions.clear()
        return sessions

    def process_logs(self, lines: int = 200):
        """
        Parse recent logs for player events.

        This should be called periodically to update player tracking state.
        """
        try:
            result = subprocess.run(
                [
                    "journalctl",
                    "-u",
                    SERVICE_NAME,
                    "-n",
                    str(lines),
                    "--no-pager",
                    "-o",
                    "short-iso",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            handshake_pattern = re.compile(LOG_PATTERNS["handshake"])
            character_pattern = re.compile(LOG_PATTERNS["character"])
            disconnect_pattern = re.compile(LOG_PATTERNS["disconnect"])

            for line in result.stdout.strip().split("\n"):
                if not line or line == self._last_processed_line:
                    continue

                # Parse timestamp from short-iso format
                # Format: 2026-01-11T23:30:08+0000
                timestamp = self._parse_iso_timestamp(line)
                if not timestamp:
                    timestamp = datetime.now()

                # Check for handshake
                handshake_match = handshake_pattern.search(line)
                if handshake_match:
                    steam_id = handshake_match.group(1)
                    self.process_handshake(steam_id, timestamp)
                    continue

                # Check for character ZDOID
                character_match = character_pattern.search(line)
                if character_match:
                    player_name = character_match.group(1)
                    self.process_character_zdoid(player_name, timestamp)
                    continue

                # Check for disconnect
                disconnect_match = disconnect_pattern.search(line)
                if disconnect_match:
                    steam_id = disconnect_match.group(1)
                    self.process_disconnect(steam_id, timestamp)
                    continue

            # Remember last line to avoid reprocessing
            lines_list = result.stdout.strip().split("\n")
            if lines_list:
                self._last_processed_line = lines_list[-1]

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    def _parse_iso_timestamp(self, line: str) -> Optional[datetime]:
        """Parse ISO timestamp from journalctl short-iso format."""
        try:
            # Format: 2026-01-11T23:30:08+0000 hostname...
            match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
            if match:
                return datetime.fromisoformat(match.group(1))
        except (ValueError, AttributeError):
            pass
        return None

    def clear_stale_pending(self, max_age_seconds: int = 60):
        """Remove pending connections older than max_age_seconds."""
        now = datetime.now()
        stale = [
            steam_id
            for steam_id, pending in self.pending.items()
            if (now - pending.handshake_time).total_seconds() > max_age_seconds
        ]
        for steam_id in stale:
            del self.pending[steam_id]
