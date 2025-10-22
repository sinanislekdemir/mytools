"""Monitoring modules for system, network, and news."""

from .cpu_monitor import CPUMonitor
from .netwatch import NetworkMonitor
from .news_cache import NewsCache
from .news_fetcher import NewsFetcher
from .news_manager import NewsManager
from .process_monitor import ProcessMonitor
from .sensors import SensorManager
from .system_monitor import GPUMonitor, MemoryMonitor
from .temperature_monitor import TemperatureMonitor

# Legacy imports for backward compatibility
from .netwatch import (
    clean_past_data,
    dump_past_data,
    get_ss_tnp_output,
    network_loop,
    toggle_hide_http,
)

# from .news import news_loop  # Legacy - will be removed
from .sensors import switch_combined, switch_hide_command, system_loop

__all__ = [
    "CPUMonitor",
    "NetworkMonitor",
    "NewsCache",
    "NewsFetcher",
    "NewsManager",
    "ProcessMonitor",
    "SensorManager",
    "GPUMonitor",
    "MemoryMonitor",
    "TemperatureMonitor",
    # Legacy functions
    "clean_past_data",
    "dump_past_data",
    "get_ss_tnp_output",
    "network_loop",
    "toggle_hide_http",
    "switch_combined",
    "switch_hide_command",
    "system_loop",
]
