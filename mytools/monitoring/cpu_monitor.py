"""CPU monitoring utilities."""

import threading
import time
from typing import Dict, List, Optional

from ..core.config import Config
from ..core.logger import Logger


class CPUMonitor:
    """Monitor CPU usage and statistics."""

    def __init__(self):
        """Initialize CPU monitor."""
        self.logger = Logger.get_logger()
        self.prev_times: Optional[List[List[int]]] = None
        # Add caching for CPU data
        self._cpu_cache = None
        self._cpu_cache_time = 0
        self._cpu_cache_timeout = 1.0  # Cache for 1 second
        self._lock = threading.Lock()

    def read_cpu_times(self) -> List[List[int]]:
        """Read CPU times from /proc/stat."""
        try:
            with open("/proc/stat", "r") as f:
                lines = f.readlines()

            cpu_times = []
            for line in lines:
                if line.startswith("cpu"):  # Get all CPU lines including cpu0, cpu1, etc.
                    times = line.split()[
                        1:8
                    ]  # Extract times (user, nice, system, idle, iowait, irq, softirq)
                    cpu_times.append(list(map(int, times)))

            return cpu_times

        except Exception as e:
            self.logger.exception(f"Error reading CPU times: {e}")
            return []

    def calculate_cpu_usage(
        self, prev_times: List[List[int]], curr_times: List[List[int]]
    ) -> List[float]:
        """Calculate CPU usage percentages."""
        cpu_usages = []

        try:
            for prev, curr in zip(prev_times, curr_times):
                prev_idle = prev[3] + prev[4]  # idle + iowait
                curr_idle = curr[3] + curr[4]

                prev_total = sum(prev)
                curr_total = sum(curr)

                total_diff = curr_total - prev_total
                idle_diff = curr_idle - prev_idle

                if total_diff > 0:
                    usage_percentage = 100 * (total_diff - idle_diff) / total_diff
                else:
                    usage_percentage = 0

                cpu_usages.append(usage_percentage)

            return cpu_usages

        except Exception as e:
            self.logger.warning(f"Error calculating CPU usage: {e}")
            return [0.0] * len(prev_times) if prev_times else [0.0]

    def get_cpu_usage_data(self) -> Dict[str, str]:
        """Get CPU usage data for all cores."""
        with self._lock:
            return self._get_cpu_usage_data_locked()

    def _get_cpu_usage_data_locked(self) -> Dict[str, str]:
        """Compute CPU usage data; caller must hold self._lock."""
        # Check cache first
        current_time = time.time()
        if (
            self._cpu_cache is not None
            and current_time - self._cpu_cache_time < self._cpu_cache_timeout
        ):
            return self._cpu_cache

        if self.prev_times is None:
            self.prev_times = self.read_cpu_times()
            # Return zeros on first call
            result = {"Total": "Calculating..."}
            self._cpu_cache = result
            self._cpu_cache_time = current_time
            return result

        curr_times = self.read_cpu_times()
        if not curr_times:
            result = {"Error": "Could not read CPU data"}
            self._cpu_cache = result
            self._cpu_cache_time = current_time
            return result

        cpu_usages = self.calculate_cpu_usage(self.prev_times, curr_times)

        result = {}
        for i, usage in enumerate(cpu_usages):
            if i == 0:
                result["Total"] = f"Total: {usage:.2f}%"
            else:
                # Add color prefixes based on thresholds
                if usage > Config.CPU_CRITICAL_THRESHOLD:
                    result[f"Core {i}"] = f"RED!{usage:.2f}%"
                elif usage > Config.CPU_WARNING_THRESHOLD:
                    result[f"Core {i}"] = f"YELLOW!{usage:.2f}%"
                else:
                    result[f"Core {i}"] = f"{usage:.2f}%"

        self.prev_times = curr_times

        # Cache the result
        self._cpu_cache = result
        self._cpu_cache_time = current_time
        return result
