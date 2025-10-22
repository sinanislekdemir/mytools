"""Process monitoring utilities."""

import os
from typing import Dict, List

from ..core.config import Config
from ..core.logger import Logger


class ProcessMonitor:
    """Monitor system processes."""

    def __init__(self):
        """Initialize process monitor."""
        self.logger = Logger.get_logger()
        # Add caching for process data
        self._cache = {}
        self._cache_time = {}
        self._cache_timeout = 1.0  # Cache for 1 second

    def bytes_to_human_readable(self, bytes_value: int) -> str:
        """Convert bytes to human-readable format."""
        kb = bytes_value / 1024
        mb = kb / 1024
        gb = mb / 1024
        tb = gb / 1024

        if tb >= 1:
            return f"{tb:.2f} TB".rjust(10, " ")
        elif gb >= 1:
            return f"{gb:.2f} GB".rjust(10, " ")
        elif mb >= 1:
            return f"{mb:.2f} MB".rjust(10, " ")
        elif kb >= 1:
            return f"{kb:.2f} KB".rjust(10, " ")
        else:
            return "0 KB".rjust(10, " ")

    def get_processes(
        self,
        n: int,
        sort_by: str = "-rss",
        combined: bool = False,
        hide_command: bool = False,
    ) -> List[List[str]]:
        """Get top N processes sorted by specified criteria."""
        try:
            import time

            # Create cache key
            cache_key = f"{n}_{sort_by}_{combined}_{hide_command}"
            current_time = time.time()

            # Check if we have cached data that's still valid
            if (
                cache_key in self._cache
                and cache_key in self._cache_time
                and current_time - self._cache_time[cache_key] < self._cache_timeout
            ):
                return self._cache[cache_key]

            # Fetch fresh data
            command = f"ps aux --sort={sort_by}"
            result = os.popen(command).read().split("\n")

            if not combined:
                processes = self._get_individual_processes(
                    result, n, sort_by, hide_command
                )
            else:
                processes = self._get_combined_processes(
                    result, n, sort_by, hide_command
                )

            # Cache the result
            self._cache[cache_key] = processes
            self._cache_time[cache_key] = current_time

            return processes

        except Exception as e:
            self.logger.exception(f"Error getting processes: {e}")
            return [["Error", "Could not retrieve process information"]]

    def _get_individual_processes(
        self, result: List[str], n: int, sort_by: str, hide_command: bool
    ) -> List[List[str]]:
        """Get individual process entries."""
        processes = [["PID", "USER", "%MEM", "%CPU", "COMMAND", "RSS", "VSZ"]]

        for line in result[1:]:
            if not line or len(processes) >= n + 1:
                break

            line_parts = line.split()
            if len(line_parts) < 11 or line_parts[10] == "ps":
                continue

            # Determine status prefix based on thresholds
            pre = self._get_process_status_prefix(line_parts, sort_by)
            command = " ".join(line_parts[10:]) if not hide_command else ""

            processes.append(
                [
                    pre + line_parts[1],  # PID with status
                    line_parts[0],  # USER
                    line_parts[3],  # %MEM
                    line_parts[2],  # %CPU
                    command,  # COMMAND
                    self.bytes_to_human_readable(int(line_parts[5])),  # RSS
                    self.bytes_to_human_readable(int(line_parts[4])),  # VSZ
                ]
            )

        return processes

    def _get_combined_processes(
        self, result: List[str], n: int, sort_by: str, hide_command: bool
    ) -> List[List[str]]:
        """Get processes combined by command name."""
        processes = [["PID", "USER", "%MEM", "%CPU", "COMMAND", "RSS", "VSZ"]]
        cmdmap = {}

        for line in result[1:]:
            if not line:
                continue

            line_parts = line.split()
            if len(line_parts) < 11 or line_parts[10] == "ps":
                continue

            cmd = line_parts[10]
            if cmd not in cmdmap:
                cmdmap[cmd] = {
                    "pid": line_parts[1],
                    "user": line_parts[0],
                    "mem": 0.0,
                    "cpu": 0.0,
                    "rss": 0,
                    "vsz": 0,
                    "command": cmd,
                }

            cmdmap[cmd]["mem"] += float(line_parts[3])
            cmdmap[cmd]["cpu"] += float(line_parts[2])
            cmdmap[cmd]["rss"] += int(line_parts[5])
            cmdmap[cmd]["vsz"] += int(line_parts[4])

        # Convert to list and sort
        proc_list = []
        for cmd, data in cmdmap.items():
            pre = self._get_combined_status_prefix(data, sort_by)
            command = data["command"] if not hide_command else ""

            proc_list.append(
                [
                    pre + data["pid"],
                    data["user"],
                    f"{data['mem']:.2f}",
                    f"{data['cpu']:.2f}",
                    command,
                    self.bytes_to_human_readable(data["rss"]),
                    self.bytes_to_human_readable(data["vsz"]),
                ]
            )

        # Sort the list
        if sort_by == "-%cpu":
            proc_list.sort(key=lambda x: float(x[3]), reverse=True)
        else:
            proc_list.sort(key=lambda x: float(x[2]), reverse=True)

        processes.extend(proc_list[:n])
        return processes

    def _get_process_status_prefix(self, line_parts: List[str], sort_by: str) -> str:
        """Get status prefix for individual process."""
        if sort_by == "-rss":
            mem = float(line_parts[3])
            if mem > Config.MEMORY_CRITICAL_THRESHOLD:
                return "RED!"
            elif mem > Config.MEMORY_WARNING_THRESHOLD:
                return "YELLOW!"
        else:  # sort by CPU
            cpu = float(line_parts[2])
            if cpu > Config.CPU_CRITICAL_THRESHOLD:
                return "RED!"
            elif cpu > Config.CPU_WARNING_THRESHOLD:
                return "YELLOW!"
        return ""

    def _get_combined_status_prefix(self, data: Dict, sort_by: str) -> str:
        """Get status prefix for combined process."""
        if sort_by == "-rss":
            if data["mem"] > Config.MEMORY_CRITICAL_THRESHOLD:
                return "RED!"
            elif data["mem"] > Config.MEMORY_WARNING_THRESHOLD:
                return "YELLOW!"
        else:  # sort by CPU
            if data["cpu"] > Config.CPU_CRITICAL_THRESHOLD:
                return "RED!"
            elif data["cpu"] > Config.CPU_WARNING_THRESHOLD:
                return "YELLOW!"
        return ""
