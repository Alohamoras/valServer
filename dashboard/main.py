#!/usr/bin/env python3
"""
Valheim Server Terminal Dashboard

A real-time terminal dashboard for monitoring your Valheim server.

Usage:
    python -m dashboard.main
    # or
    ./dashboard/main.py
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Event
from typing import Optional

from rich.live import Live

from .config import RefreshConfig
from .collectors.server import get_server_status, ServerStatus
from .collectors.system import get_system_stats, SystemStats
from .collectors.logs import get_recent_logs, LogEntry
from .collectors.players import SessionTracker, OnlinePlayer
from .storage.player_stats import PlayerStatsStorage, PlayerStats
from .ui.layout import create_layout
from .ui.panels import (
    render_header,
    render_footer,
    render_server_panel,
    render_system_panel,
    render_online_players_panel,
    render_player_stats_panel,
    render_logs_panel,
)


class DashboardState:
    """Thread-safe state container for dashboard data."""

    def __init__(self):
        self.server_status: Optional[ServerStatus] = None
        self.system_stats: Optional[SystemStats] = None
        self.online_players: list[OnlinePlayer] = []
        self.player_stats: list[tuple[str, PlayerStats]] = []
        self.recent_logs: list[LogEntry] = []


class Dashboard:
    """Main dashboard controller."""

    def __init__(self, config: Optional[RefreshConfig] = None):
        self.config = config or RefreshConfig()
        self.state = DashboardState()
        self.stop_event = Event()
        self.layout = create_layout()

        # Initialize components
        self.session_tracker = SessionTracker()
        self.stats_storage = PlayerStatsStorage()
        self.stats_storage.load()

        # Load existing player stats
        self.state.player_stats = self.stats_storage.get_players_sorted_by_playtime()

    def _update_server_status(self):
        """Background task: Update server status."""
        while not self.stop_event.is_set():
            try:
                self.state.server_status = get_server_status()
            except Exception:
                pass  # Keep last known state on error
            self.stop_event.wait(self.config.server_status)

    def _update_system_stats(self):
        """Background task: Update system statistics."""
        while not self.stop_event.is_set():
            try:
                self.state.system_stats = get_system_stats()
            except Exception:
                pass
            self.stop_event.wait(self.config.system_stats)

    def _update_logs(self):
        """Background task: Fetch recent logs."""
        while not self.stop_event.is_set():
            try:
                self.state.recent_logs = get_recent_logs(lines=12)
            except Exception:
                pass
            self.stop_event.wait(self.config.logs)

    def _update_player_tracking(self):
        """Background task: Process log events for player tracking."""
        while not self.stop_event.is_set():
            try:
                # Process new log events
                self.session_tracker.process_logs(lines=100)

                # Clean up stale pending connections
                self.session_tracker.clear_stale_pending()

                # Update online players
                self.state.online_players = self.session_tracker.get_online_players()

                # Process completed sessions and update stats
                completed = self.session_tracker.get_and_clear_completed_sessions()
                for session in completed:
                    self.stats_storage.update_player_session(
                        steam_id=session.steam_id,
                        player_name=session.player_name,
                        session_duration_seconds=session.duration_seconds,
                        connect_time=session.connect_time,
                    )

                # Save if there were completed sessions
                if completed:
                    self.stats_storage.save()

            except Exception:
                pass

            self.stop_event.wait(self.config.player_tracking)

    def _update_player_stats(self):
        """Background task: Refresh player statistics from storage."""
        while not self.stop_event.is_set():
            try:
                self.state.player_stats = (
                    self.stats_storage.get_players_sorted_by_playtime()
                )
            except Exception:
                pass
            self.stop_event.wait(self.config.player_stats)

    def _render(self):
        """Render current state to Rich Layout."""
        self.layout["header"].update(render_header())
        self.layout["server_status"].update(
            render_server_panel(self.state.server_status)
        )
        self.layout["system_stats"].update(
            render_system_panel(self.state.system_stats)
        )
        self.layout["players_online"].update(
            render_online_players_panel(self.state.online_players)
        )
        self.layout["player_stats"].update(
            render_player_stats_panel(self.state.player_stats)
        )
        self.layout["logs"].update(render_logs_panel(self.state.recent_logs))
        self.layout["footer"].update(render_footer())

        return self.layout

    def run(self):
        """Start the dashboard with Live display."""
        # Start background update threads
        threads = [
            Thread(target=self._update_server_status, daemon=True, name="server_status"),
            Thread(target=self._update_system_stats, daemon=True, name="system_stats"),
            Thread(target=self._update_logs, daemon=True, name="logs"),
            Thread(target=self._update_player_tracking, daemon=True, name="player_tracking"),
            Thread(target=self._update_player_stats, daemon=True, name="player_stats"),
        ]

        for t in threads:
            t.start()

        try:
            with Live(
                self._render(),
                refresh_per_second=1,
                screen=True,
                transient=True,
            ) as live:
                while not self.stop_event.is_set():
                    live.update(self._render())
                    time.sleep(self.config.display)

        except KeyboardInterrupt:
            pass
        finally:
            self.stop_event.set()

            # Save any pending stats
            try:
                self.stats_storage.save()
            except Exception:
                pass

            print("\nDashboard stopped.")


def main():
    """Entry point for the dashboard."""
    # Check if running from correct location
    dashboard = Dashboard()
    dashboard.run()


if __name__ == "__main__":
    # Allow running as a script
    # Add parent directory to path for imports
    script_dir = Path(__file__).parent.parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    main()
