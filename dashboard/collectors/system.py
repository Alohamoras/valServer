"""System statistics collector using psutil."""

import psutil
from dataclasses import dataclass
from typing import Optional

from ..config import VALHEIM_DIR


@dataclass
class SystemStats:
    """System resource usage statistics."""

    cpu_percent: float
    memory_total_gb: float
    memory_used_gb: float
    memory_percent: float
    disk_total_gb: float
    disk_free_gb: float
    disk_percent: float
    valheim_cpu_percent: Optional[float] = None
    valheim_memory_mb: Optional[float] = None


def get_system_stats() -> SystemStats:
    """Get current system resource usage."""
    # CPU (non-blocking, uses cached value from previous call)
    cpu_percent = psutil.cpu_percent(interval=None)

    # Memory
    mem = psutil.virtual_memory()

    # Disk - use root if Valheim dir doesn't exist or isn't accessible
    disk_path = "/"
    try:
        if VALHEIM_DIR.exists():
            disk_path = str(VALHEIM_DIR)
    except (OSError, PermissionError):
        pass

    try:
        disk = psutil.disk_usage(disk_path)
    except OSError:
        disk = psutil.disk_usage("/")

    # Find Valheim process stats
    valheim_cpu = None
    valheim_mem = None

    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            name = proc.info.get("name", "").lower()
            cmdline = proc.info.get("cmdline", [])

            # Check for valheim_server.x86_64 process
            if "valheim" in name and "server" in name:
                valheim_cpu = proc.cpu_percent()
                valheim_mem = proc.memory_info().rss / (1024 * 1024)
                break

            # Also check command line for valheim
            cmdline_str = " ".join(cmdline).lower() if cmdline else ""
            if "valheim_server" in cmdline_str:
                valheim_cpu = proc.cpu_percent()
                valheim_mem = proc.memory_info().rss / (1024 * 1024)
                break

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return SystemStats(
        cpu_percent=cpu_percent,
        memory_total_gb=mem.total / (1024**3),
        memory_used_gb=mem.used / (1024**3),
        memory_percent=mem.percent,
        disk_total_gb=disk.total / (1024**3),
        disk_free_gb=disk.free / (1024**3),
        disk_percent=disk.percent,
        valheim_cpu_percent=valheim_cpu,
        valheim_memory_mb=valheim_mem,
    )
