"""Rich Layout structure for the dashboard."""

from rich.layout import Layout


def create_layout() -> Layout:
    """Create the main dashboard layout structure."""
    layout = Layout()

    # Main vertical split: header, body, footer
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )

    # Body split: top row (status/system), players sections, logs
    layout["body"].split_column(
        Layout(name="top_row", size=8),
        Layout(name="players_online", size=7),
        Layout(name="player_stats", size=10),
        Layout(name="logs"),  # Takes remaining space
    )

    # Top row: server status | system stats
    layout["top_row"].split_row(
        Layout(name="server_status"),
        Layout(name="system_stats"),
    )

    return layout
