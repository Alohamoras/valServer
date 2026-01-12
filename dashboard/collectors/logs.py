"""Log collector and parser for Valheim server logs."""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..config import SERVICE_NAME, LOG_NOISE_PATTERNS


@dataclass
class LogEntry:
    """A parsed log entry."""

    timestamp: datetime
    message: str
    level: str = "info"  # "info", "warning", "error"


def get_recent_logs(lines: int = 15, filter_noise: bool = True) -> list[LogEntry]:
    """
    Get recent server logs from journalctl.

    Args:
        lines: Number of log entries to return
        filter_noise: If True, filter out routine/noisy messages
    """
    try:
        # Fetch more lines than needed to account for filtering
        fetch_count = lines * 3 if filter_noise else lines

        result = subprocess.run(
            ["journalctl", "-u", SERVICE_NAME, "-n", str(fetch_count), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        logs = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            # Filter noise if enabled
            if filter_noise and any(p in line for p in LOG_NOISE_PATTERNS):
                continue

            entry = _parse_log_line(line)
            if entry:
                logs.append(entry)

        # Return only the requested count (most recent)
        return logs[-lines:]

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _parse_log_line(line: str) -> Optional[LogEntry]:
    """Parse a single log line into a LogEntry."""
    try:
        # journalctl format: "Jan 11 23:30:08 hostname start_server.sh[PID]: message"
        # We want to extract the game timestamp if present, or use journal timestamp

        # First, try to extract the game's own timestamp
        # Format: "01/11/2026 23:30:08: message"
        game_ts_match = re.search(
            r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}):\s*(.+)$", line
        )

        if game_ts_match:
            ts_str = game_ts_match.group(1)
            message = game_ts_match.group(2).strip()

            try:
                timestamp = datetime.strptime(ts_str, "%m/%d/%Y %H:%M:%S")
            except ValueError:
                timestamp = datetime.now()
        else:
            # Fall back to journal timestamp
            # Format: "Jan 11 23:30:08"
            journal_match = re.match(
                r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+\S+\s+\S+:\s*(.+)$", line
            )

            if journal_match:
                ts_str = journal_match.group(1)
                message = journal_match.group(2).strip()

                try:
                    # Add current year since journal format doesn't include it
                    current_year = datetime.now().year
                    timestamp = datetime.strptime(
                        f"{current_year} {ts_str}", "%Y %b %d %H:%M:%S"
                    )
                except ValueError:
                    timestamp = datetime.now()
            else:
                # Can't parse, use current time and full line as message
                timestamp = datetime.now()
                message = line.strip()

        # Determine log level based on content
        level = "info"
        message_lower = message.lower()
        if "error" in message_lower or "exception" in message_lower:
            level = "error"
        elif "warning" in message_lower or "warn" in message_lower:
            level = "warning"

        return LogEntry(timestamp=timestamp, message=message, level=level)

    except Exception:
        return None
