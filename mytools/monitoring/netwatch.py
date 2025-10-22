"""Refactored network monitoring module."""

import curses
import socket
import subprocess
import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from ..core.config import Config
from ..core.logger import Logger


class NetworkMonitor:
    """Network monitoring with improved structure."""

    def __init__(self):
        """Initialize network monitor."""
        self.logger = Logger.get_logger()
        self.past_data: Dict[str, List] = {}
        self.hide_http = False
        self.network_list = {}
        # Add scrolling state
        self.scroll_offset = 0
        self.selected_line = 0

    @lru_cache(maxsize=128)
    def reverse_nslookup(self, ip: str) -> str:
        """Perform reverse DNS lookup with caching."""
        try:
            host, _, _ = socket.gethostbyaddr(ip)
            return host
        except Exception as e:
            self.logger.debug(f"Reverse lookup failed for {ip}: {e}")
            return ip

    def time_to_str(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02}:{minutes:02}:{secs:02}"

    def clean_past_data(self) -> None:
        """Remove inactive connections from past data."""
        try:
            keys_to_remove = []
            for key, value in self.past_data.items():
                if not value[6]:  # Not active
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self.past_data[key]

            self.logger.info(f"Cleaned {len(keys_to_remove)} inactive connections")

        except Exception as e:
            self.logger.exception(f"Error cleaning past data: {e}")

    def dump_past_data(self) -> None:
        """Dump past data to a CSV file."""
        try:
            filename = f"{Config.NETWORK_CSV_PREFIX}{int(time.time())}.csv"
            with open(filename, "w") as f:
                f.write("State,Local Address,Peer Address,Process,Reverse NS,Time\n")
                for key, value in self.past_data.items():
                    # Clean commas from process names
                    cleaned_value = value.copy()
                    cleaned_value[3] = cleaned_value[3].replace(",", " ")
                    row = ",".join(str(v) for v in cleaned_value[:5])
                    f.write(row + "\n")

            self.logger.info(f"Network data dumped to {filename}")

        except Exception as e:
            self.logger.exception(f"Error dumping network data: {e}")

    def toggle_hide_http(self) -> None:
        """Toggle hiding HTTP/HTTPS connections."""
        self.hide_http = not self.hide_http
        self.logger.debug(f"HTTP hiding toggled: {self.hide_http}")

    def update_network_data(self) -> None:
        """Update network connection data using ss command."""
        try:
            result = subprocess.run(
                ["ss", "-tnpH"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )

            if result.returncode != 0:
                self.logger.warning(f"ss command failed: {result.stderr.decode()}")
                return

            lines = result.stdout.decode("utf-8").split("\n")
            current_connections = set()

            for line in lines:
                if not line.strip():
                    continue

                connection_data = self._parse_ss_line(line)
                if connection_data:
                    key, data = connection_data
                    current_connections.add(key)

                    if key not in self.past_data:
                        # New connection
                        self.past_data[key] = data + [time.monotonic(), True]
                    else:
                        # Existing connection - update active status
                        self.past_data[key][6] = True

            # Mark disconnected connections
            self._mark_disconnected_connections(current_connections)

            # Update display data
            self._update_display_data()

        except subprocess.TimeoutExpired:
            self.logger.warning("ss command timed out")
        except Exception as e:
            self.logger.exception(f"Error updating network data: {e}")

    def _parse_ss_line(self, line: str) -> Optional[Tuple[str, List[str]]]:
        """Parse a single line from ss output."""
        try:
            parts = [part.strip() for part in line.split()]
            if len(parts) < 4:
                return None

            # Ensure we have at least 6 parts (pad with empty strings if needed)
            while len(parts) < 6:
                parts.append("")

            state = parts[0]
            local_addr = parts[3]
            peer_addr = parts[4]
            process = parts[5]

            # Generate unique key
            key = f"{local_addr}{peer_addr}{process}"

            # Perform reverse lookup for peer address
            peer_ip = peer_addr.split(":")[0]
            reverse_ns = self.reverse_nslookup(peer_ip)

            return key, [state, local_addr, peer_addr, process, reverse_ns]

        except Exception as e:
            self.logger.debug(f"Error parsing ss line '{line}': {e}")
            return None

    def _mark_disconnected_connections(self, current_connections: set) -> None:
        """Mark connections that are no longer active."""
        for key in self.past_data:
            if key not in current_connections and self.past_data[key][6]:
                # Connection is no longer active
                self.past_data[key][6] = False
                self.past_data[key][5] = time.monotonic() - self.past_data[key][5]

    def _update_display_data(self) -> None:
        """Update the data structure for display."""
        display_list = []

        # Add header
        display_list.append(
            ["State", "Local Address", "Peer Address", "Process", "Reverse NS", "Time"]
        )

        # Process connections for display
        for key, value in self.past_data.items():
            if self.hide_http and self._is_http_connection(value[2]):
                continue

            # Filter by excluded processes
            if self._is_process_excluded(value[3]):  # value[3] is process name
                continue

            display_row = self._format_display_row(value)
            display_list.append(display_row)

        # Sort by status (active first) and time
        display_list[1:] = sorted(
            display_list[1:], key=lambda x: (x[0].startswith("RED!"), x[5])
        )

        self.network_list = {"Network": display_list}

    def _is_http_connection(self, peer_addr: str) -> bool:
        """Check if connection is HTTP/HTTPS."""
        try:
            port = peer_addr.split(":")[1]
            return port in ["80", "443"]
        except (IndexError, ValueError):
            return False

    def _is_process_excluded(self, process_name: str) -> bool:
        """Check if a process should be excluded based on keywords."""
        return Config.is_process_excluded(process_name)

    def _format_display_row(self, value: List) -> List[str]:
        """Format a connection for display."""
        if not value[6]:  # Inactive connection
            return [
                f"RED!{value[0]}",
                value[1],
                value[2],
                value[3],
                value[4],
                self.time_to_str(value[5]),
            ]
        else:  # Active connection
            now = time.monotonic()
            duration = now - value[5]

            prefix = ""
            if duration < 30:  # New connection (less than 30 seconds)
                prefix = "GREEN!"

            return [
                f"{prefix}{value[0]}",
                value[1],
                value[2],
                value[3],
                value[4],
                self.time_to_str(duration),
            ]

    def display_network_info(self, stdscr: curses.window) -> None:
        """Display network information on screen with scrolling."""
        try:
            from ..core.ui import draw_panel_with_scrolling

            height, width = stdscr.getmaxyx()

            display_data = {}
            if "Network" in self.network_list:
                display_data["Network"] = self.network_list["Network"]

            # Use scrolling panel with active highlighting
            draw_panel_with_scrolling(
                stdscr,
                "Network [↑↓: Scroll]",
                display_data,
                1,
                0,
                width,
                height - 1,
                scroll_offset=self.scroll_offset,
                is_active=True,  # Always active in network mode
                selected_line=self.selected_line,
            )

        except Exception as e:
            self.logger.exception(f"Error displaying network info: {e}")

    def scroll_network(self, direction: int):
        """Scroll the network list up (-1) or down (1)."""
        if "Network" in self.network_list and self.network_list["Network"]:
            # Move the selected line
            self.selected_line += direction
            self.selected_line = max(0, self.selected_line)

            # Limit to available data
            max_items = len(self.network_list["Network"]) - 1  # Exclude header
            if max_items > 0:
                self.selected_line = min(self.selected_line, max_items - 1)

            # Auto-scroll the panel if needed
            panel_height = 10  # Approximate visible lines in network panel

            # If selected line is above visible area, scroll up
            if self.selected_line < self.scroll_offset:
                self.scroll_offset = self.selected_line
            # If selected line is below visible area, scroll down
            elif self.selected_line >= self.scroll_offset + panel_height:
                self.scroll_offset = self.selected_line - panel_height + 1

            # Ensure scroll doesn't go negative
            self.scroll_offset = max(0, self.scroll_offset)


# Legacy functions for backward compatibility
past_data = {}
hide_http = False
network_list = {}
_network_monitor = None


def get_network_monitor():
    """Get or create network monitor instance."""
    global _network_monitor
    if _network_monitor is None:
        _network_monitor = NetworkMonitor()
    return _network_monitor


def clean_past_data():
    """Legacy function."""
    get_network_monitor().clean_past_data()


def dump_past_data():
    """Legacy function."""
    get_network_monitor().dump_past_data()


def toggle_hide_http():
    """Legacy function."""
    get_network_monitor().toggle_hide_http()


def get_ss_tnp_output():
    """Legacy function."""
    get_network_monitor().update_network_data()


def network_loop(stdscr: curses.window):
    """Legacy function."""
    get_network_monitor().display_network_info(stdscr)
