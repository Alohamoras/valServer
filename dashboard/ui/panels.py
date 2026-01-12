"""Panel rendering functions for the dashboard."""

from datetime import datetime
from typing import Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from ..collectors.server import ServerStatus
from ..collectors.system import SystemStats
from ..collectors.logs import LogEntry
from ..collectors.players import OnlinePlayer
from ..storage.player_stats import PlayerStats


def format_duration(seconds: Optional[int]) -> str:
    """Format seconds into a human-readable duration."""
    if seconds is None or seconds < 0:
        return "N/A"

    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"

    hours = minutes // 60
    remaining_minutes = minutes % 60
    if hours < 24:
        return f"{hours}h {remaining_minutes}m"

    days = hours // 24
    remaining_hours = hours % 24
    return f"{days}d {remaining_hours}h"


def format_relative_time(dt: Optional[datetime]) -> str:
    """Format a datetime as relative time (e.g., 'Today', '3 days ago')."""
    if dt is None:
        return "Unknown"

    now = datetime.now()
    delta = now - dt

    if delta.days == 0:
        return "Today"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    elif delta.days < 30:
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    else:
        return dt.strftime("%Y-%m-%d")


def render_header() -> Panel:
    """Render the header panel."""
    title = Text("VALHEIM SERVER DASHBOARD", style="bold white")
    return Panel(
        Align.center(title),
        style="blue",
        border_style="blue",
    )


def render_footer() -> Panel:
    """Render the footer panel."""
    now = datetime.now().strftime("%H:%M:%S")
    text = Text(f"Last updated: {now}  |  Press Ctrl+C to exit", style="dim")
    return Panel(
        Align.center(text),
        style="dim",
        border_style="dim",
    )


def render_server_panel(status: Optional[ServerStatus]) -> Panel:
    """Render the server status panel."""
    if status is None:
        content = Text("Loading...", style="yellow")
        return Panel(content, title="Server Status", border_style="yellow")

    lines = []

    if status.running:
        status_line = Text()
        status_line.append("  ", style="green")
        status_line.append(" Running", style="green bold")
        lines.append(status_line)

        if status.uptime_seconds:
            lines.append(Text(f"  Uptime: {format_duration(status.uptime_seconds)}"))

        if status.memory_mb:
            lines.append(Text(f"  Memory: {status.memory_mb:.0f} MB"))

        if status.world_name:
            lines.append(Text(f"  World: {status.world_name}"))

        if status.server_name:
            lines.append(Text(f"  Server: {status.server_name}", style="dim"))

        lines.append(Text(f"  Players: {status.current_connections}"))

        border_style = "green"
    else:
        status_line = Text()
        status_line.append("  ", style="red")
        status_line.append(" Stopped", style="red bold")
        lines.append(status_line)
        lines.append(Text(f"  State: {status.state}", style="dim"))
        border_style = "red"

    content = Text("\n").join(lines)
    return Panel(content, title="Server Status", border_style=border_style)


def render_system_panel(stats: Optional[SystemStats]) -> Panel:
    """Render the system statistics panel."""
    if stats is None:
        content = Text("Loading...", style="yellow")
        return Panel(content, title="System Stats", border_style="yellow")

    lines = []

    # CPU
    cpu_style = "green" if stats.cpu_percent < 70 else "yellow" if stats.cpu_percent < 90 else "red"
    lines.append(Text(f"  CPU: {stats.cpu_percent:.1f}%", style=cpu_style))

    # RAM
    ram_style = "green" if stats.memory_percent < 70 else "yellow" if stats.memory_percent < 90 else "red"
    lines.append(
        Text(
            f"  RAM: {stats.memory_used_gb:.1f}/{stats.memory_total_gb:.1f} GB ({stats.memory_percent:.0f}%)",
            style=ram_style,
        )
    )

    # Disk
    disk_style = "green" if stats.disk_percent < 80 else "yellow" if stats.disk_percent < 95 else "red"
    lines.append(
        Text(f"  Disk: {stats.disk_free_gb:.0f} GB free ({100 - stats.disk_percent:.0f}%)", style=disk_style)
    )

    # Valheim process stats if available
    if stats.valheim_memory_mb is not None:
        lines.append(Text(""))
        lines.append(Text("  Valheim Process:", style="dim"))
        lines.append(Text(f"    Memory: {stats.valheim_memory_mb:.0f} MB", style="dim"))
        if stats.valheim_cpu_percent is not None:
            lines.append(Text(f"    CPU: {stats.valheim_cpu_percent:.1f}%", style="dim"))

    content = Text("\n").join(lines)
    return Panel(content, title="System Stats", border_style="blue")


def render_online_players_panel(players: list[OnlinePlayer]) -> Panel:
    """Render the currently online players panel."""
    if not players:
        content = Text("  No players online", style="dim italic")
        return Panel(content, title="Players Online (0)", border_style="dim")

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Name", style="cyan")
    table.add_column("Session Time", justify="right")

    for player in players:
        table.add_row(
            player.name,
            format_duration(player.session_duration_seconds),
        )

    return Panel(table, title=f"Players Online ({len(players)})", border_style="cyan")


def render_player_stats_panel(players: list[tuple[str, PlayerStats]]) -> Panel:
    """Render the player statistics panel."""
    if not players:
        content = Text("  No player history yet", style="dim italic")
        return Panel(content, title="Player Statistics", border_style="dim")

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Name", style="white")
    table.add_column("Total Playtime", justify="right")
    table.add_column("Sessions", justify="right")
    table.add_column("Last Online", justify="right")

    # Show top 10 players by playtime
    for steam_id, stats in players[:10]:
        last_seen_dt = stats.last_seen_dt
        table.add_row(
            stats.name,
            format_duration(stats.total_playtime_seconds),
            str(stats.session_count),
            format_relative_time(last_seen_dt),
        )

    title = f"Player Statistics ({len(players)} total)"
    return Panel(table, title=title, border_style="magenta")


def render_logs_panel(logs: list[LogEntry]) -> Panel:
    """Render the recent logs panel."""
    if not logs:
        content = Text("  No recent logs", style="dim italic")
        return Panel(content, title="Recent Logs", border_style="dim")

    lines = []
    for entry in logs:
        time_str = entry.timestamp.strftime("%H:%M:%S")

        # Style based on log level
        if entry.level == "error":
            style = "red"
        elif entry.level == "warning":
            style = "yellow"
        else:
            style = "white"

        # Truncate long messages
        message = entry.message
        if len(message) > 80:
            message = message[:77] + "..."

        line = Text()
        line.append(f"[{time_str}] ", style="dim")
        line.append(message, style=style)
        lines.append(line)

    content = Text("\n").join(lines)
    return Panel(content, title="Recent Logs", border_style="dim")
