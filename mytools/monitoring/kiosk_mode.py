"""Kiosk mode - Home page with system stats and newsfeed."""

import curses
import time
from threading import Thread, Lock
from typing import List, Optional, Tuple

from ..core.config import Config
from ..core.logger import Logger
from ..core.themes import ColorPair, BoxChars
from .news_fetcher import NewsFetcher
from .news_cache import NewsCache
from .sensors import get_sensor_manager


class KioskMode:
    """Kiosk mode displaying system stats and rotating newsfeed."""

    def __init__(self):
        """Initialize kiosk mode."""
        self.logger = Logger.get_logger()
        self.news_cache = NewsCache()
        self.news_fetcher = NewsFetcher(self.news_cache)

        # News data
        self.news_items: List[Tuple[str, str]] = []  # (source_name, title)
        self.news_lock = Lock()
        self.last_news_update = 0
        self.news_update_interval = 60  # seconds

        # News sources (get first 3)
        all_sources = Config.get_news_sources()
        self.news_sources = all_sources[:3] if len(all_sources) >= 3 else all_sources

        # Background thread
        self.running = False
        self.news_thread: Optional[Thread] = None

        # Cache for previous display state to avoid redrawing unchanged content
        self._prev_gpu_temp = None
        self._prev_vram = None
        self._prev_ram = None
        self._prev_swap = None
        self._prev_cpu_apps = None
        self._prev_mem_apps = None
        self._prev_news_items = None
        self._prev_clocks = None
        self._first_draw = True

    def start(self):
        """Start background news fetching."""
        self.running = True
        self.news_thread = Thread(target=self._news_update_loop, daemon=True)
        self.news_thread.start()
        # Initial fetch
        self._fetch_news()

    def stop(self):
        """Stop background news fetching."""
        self.running = False
        if self.news_thread:
            self.news_thread.join(timeout=1)

    def _news_update_loop(self):
        """Background thread to update news every minute."""
        while self.running:
            current_time = time.time()
            if current_time - self.last_news_update >= self.news_update_interval:
                self._fetch_news()
                self.last_news_update = current_time
            time.sleep(1)

    def _fetch_news(self):
        """Fetch news from the first 3 sources."""
        try:
            new_items = []
            for source_url in self.news_sources:
                try:
                    # Extract source name from URL
                    source_name = self._extract_source_name(source_url)
                    items = self.news_fetcher.fetch_news(source_url)
                    for item in items:
                        new_items.append((source_name, item))
                except Exception as e:
                    self.logger.error(f"Error fetching from {source_url}: {e}")

            with self.news_lock:
                self.news_items = new_items

        except Exception as e:
            self.logger.error(f"Error in news fetch: {e}")

    def _extract_source_name(self, url: str) -> str:
        """Extract a short name from the source URL."""
        try:
            # Get domain name
            parts = url.split("//")[-1].split("/")[0].split(".")
            # Return the main domain part
            if len(parts) >= 2:
                return parts[-2].upper()
            return parts[0].upper()
        except (IndexError, AttributeError):
            return "NEWS"

    def _get_gpu_cpu_temp(self) -> Tuple[Optional[str], Optional[str]]:
        """Get GPU and CPU temperatures."""
        gpu_temp = None
        cpu_temp = None

        # Get GPU temperature
        try:
            sensor_mgr = get_sensor_manager()
            gpu_data = sensor_mgr.gpu_monitor.get_nvidia_info(50)

            if "Error" not in gpu_data:
                gpu_temp = gpu_data.get("GPU temp", "N/A").strip()
        except Exception as e:
            self.logger.debug(f"Could not get GPU temp: {e}")

        # Get CPU temperature from thermal zones
        try:
            sensor_mgr = get_sensor_manager()
            thermal_zones = sensor_mgr.temperature_monitor.get_thermal_zones()

            self.logger.debug(f"Available thermal zones: {thermal_zones}")

            # Look for CPU-related thermal zones
            cpu_zone_keywords = ["x86_pkg_temp", "coretemp", "cpu", "soc"]

            for zone in thermal_zones:
                temp_data = sensor_mgr.temperature_monitor.read_temperature(zone)
                self.logger.debug(f"Zone {zone}: {temp_data}")
                if not temp_data.get("error", True):
                    zone_type = temp_data.get("type", "").lower()
                    # Check if this is a CPU-related zone
                    if any(keyword in zone_type for keyword in cpu_zone_keywords):
                        temp_val = temp_data.get("temp", 0)
                        cpu_temp = f"{temp_val:.1f}°C"
                        self.logger.info(f"Found CPU temp in {zone}: {cpu_temp}")
                        break

            # If no specific CPU zone found, use the first available thermal zone
            if not cpu_temp and thermal_zones:
                temp_data = sensor_mgr.temperature_monitor.read_temperature(
                    thermal_zones[0]
                )
                if not temp_data.get("error", True):
                    temp_val = temp_data.get("temp", 0)
                    cpu_temp = f"{temp_val:.1f}°C"
                    self.logger.info(f"Using first zone for CPU temp: {cpu_temp}")

            # If still no temp, try sensors command
            if not cpu_temp:
                cpu_temp = self._get_cpu_temp_from_sensors()

        except Exception as e:
            self.logger.error(f"Could not get CPU temp: {e}", exc_info=True)

        return gpu_temp, cpu_temp

    def _get_cpu_temp_from_sensors(self) -> Optional[str]:
        """Try to get CPU temp using sensors command."""
        import subprocess

        try:
            result = subprocess.run(
                ["sensors"], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.split("\n")
                # Look for CPU or Core temperature lines
                for line in lines:
                    lower_line = line.lower()
                    if (
                        "core" in lower_line
                        or "cpu" in lower_line
                        or "package" in lower_line
                    ) and "°c" in lower_line:
                        # Extract temperature value
                        # Format usually: "Core 0:        +45.0°C"
                        import re

                        match = re.search(r"\+?(\d+\.?\d*)\s*°c", line, re.IGNORECASE)
                        if match:
                            temp_val = float(match.group(1))
                            self.logger.info(
                                f"Found CPU temp from sensors: {temp_val}°C"
                            )
                            return f"{temp_val:.1f}°C"
        except Exception as e:
            self.logger.debug(f"Could not get CPU temp from sensors: {e}")
        return None

    def _get_vram_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get VRAM info using existing GPU monitor."""
        try:
            sensor_mgr = get_sensor_manager()
            gpu_data = sensor_mgr.gpu_monitor.get_nvidia_info(50)

            if "Error" in gpu_data:
                return None, None

            # Extract memory info
            mem_used = gpu_data.get("Memory used", "N/A").strip()
            mem_total = gpu_data.get("Memory total", "N/A").strip()

            return mem_used, mem_total
        except Exception as e:
            self.logger.debug(f"Could not get VRAM info: {e}")
            return None, None

    def _parse_memory_string(self, mem_str: str) -> Tuple[int, int]:
        """Parse memory string like 'Available 1234 MB Total: 5678 MB' to get avail and used."""
        try:
            parts = mem_str.split()
            avail_idx = parts.index("Available") + 1
            total_idx = parts.index("Total:") + 1

            avail_val = float(parts[avail_idx])
            avail_unit = parts[avail_idx + 1]
            total_val = float(parts[total_idx])
            total_unit = parts[total_idx + 1]

            # Convert to MB
            avail_mb = int(avail_val * 1024 if "GB" in avail_unit else avail_val)
            total_mb = int(total_val * 1024 if "GB" in total_unit else total_val)
            used_mb = total_mb - avail_mb

            return avail_mb, used_mb
        except Exception as e:
            self.logger.debug(f"Error parsing memory string: {e}")
            return 0, 0

    def _get_memory_info(self) -> Tuple[int, int]:
        """Get RAM available/used in MB using existing memory monitor."""
        try:
            sensor_mgr = get_sensor_manager()
            mem_info = sensor_mgr.memory_monitor.get_memory_info()
            ram_str = mem_info.get("Ram ", "")
            return self._parse_memory_string(ram_str)
        except Exception as e:
            self.logger.error(f"Error getting memory info: {e}")
            return 0, 0

    def _get_swap_info(self) -> Tuple[int, int]:
        """Get Swap available/used in MB using existing memory monitor."""
        try:
            sensor_mgr = get_sensor_manager()
            mem_info = sensor_mgr.memory_monitor.get_memory_info()
            swap_str = mem_info.get("Swap", "")
            return self._parse_memory_string(swap_str)
        except Exception as e:
            self.logger.error(f"Error getting swap info: {e}")
            return 0, 0

    def _get_top_cpu_apps(self, count: int = 3) -> List[Tuple[str, float]]:
        """Get top N CPU using apps from existing process monitor."""
        try:
            sensor_mgr = get_sensor_manager()
            processes = sensor_mgr.process_monitor.get_processes(
                count + 1, "-%cpu", False, False
            )

            # Skip header row and parse
            result = []
            for proc in processes[1 : count + 1]:
                if len(proc) >= 5:
                    # proc = [PID, USER, %MEM, %CPU, COMMAND, RSS, VSZ]
                    command = proc[4]  # COMMAND
                    cpu_percent = float(proc[3])  # %CPU

                    # Extract smart name (basename for binaries, script name for interpreters)
                    smart_name = self._extract_smart_process_name(command)
                    result.append((smart_name, cpu_percent))

            return result
        except Exception as e:
            self.logger.error(f"Error getting CPU apps: {e}")
            return []

    def _get_top_memory_apps(self, count: int = 3) -> List[Tuple[str, str]]:
        """Get top N memory using apps from existing process monitor."""
        try:
            sensor_mgr = get_sensor_manager()
            processes = sensor_mgr.process_monitor.get_processes(
                count + 1, "-rss", False, False
            )

            # Skip header row and parse
            result = []
            for proc in processes[1 : count + 1]:
                if len(proc) >= 6:
                    # proc = [PID, USER, %MEM, %CPU, COMMAND, RSS, VSZ]
                    command = proc[4]  # COMMAND
                    rss = proc[5].strip()  # RSS (already formatted)

                    # Extract smart name (basename for binaries, script name for interpreters)
                    smart_name = self._extract_smart_process_name(command)
                    result.append((smart_name, rss))

            return result
        except Exception as e:
            self.logger.error(f"Error getting memory apps: {e}")
            return []

    def _extract_smart_process_name(self, command: str) -> str:
        """Extract a smart process name: basename for binaries, script name for interpreters."""
        import os

        if not command:
            return "unknown"

        parts = command.split()
        if not parts:
            return "unknown"

        # Get the executable (first part)
        executable = os.path.basename(parts[0])

        # Check if it's an interpreter (python, node, etc.)
        interpreters = [
            "python",
            "python2",
            "python3",
            "node",
            "nodejs",
            "ruby",
            "perl",
            "php",
            "bash",
            "sh",
        ]

        # Check if executable starts with any interpreter name
        is_interpreter = any(executable.startswith(interp) for interp in interpreters)

        if is_interpreter and len(parts) > 1:
            # For interpreters, find the script name (skip flags)
            for part in parts[1:]:
                if not part.startswith("-") and part != executable:
                    # Found a script name, return basename with extension
                    script_name = os.path.basename(part)
                    return script_name
            # No script found, return interpreter name
            return executable
        else:
            # For regular binaries, return basename
            return executable

    def display(self, stdscr: curses.window):
        """Display the kiosk mode with selective redrawing."""
        height, width = stdscr.getmaxyx()

        # Only clear on first draw or mode change
        if self._first_draw:
            stdscr.clear()
            self._first_draw = False

        # Get all data
        gpu_temp, cpu_temp = self._get_gpu_cpu_temp()
        vram_used_str, vram_total_str = self._get_vram_info()
        ram_avail, ram_used = self._get_memory_info()
        swap_avail, swap_used = self._get_swap_info()
        top_cpu = self._get_top_cpu_apps(3)
        top_mem = self._get_top_memory_apps(3)

        # Left column - System Stats (compact layout)
        left_column_width = 40  # Fixed width for consistent layout

        y = 1  # Start from top row
        x_left = 2

        # GPU/CPU Temperature (only redraw if changed)
        temp_info = (gpu_temp, cpu_temp)
        if temp_info != self._prev_gpu_temp:
            temp_parts = []
            if gpu_temp:
                temp_parts.append(f"GPU: {gpu_temp}")
            if cpu_temp:
                temp_parts.append(f"CPU: {cpu_temp}")

            # Display on same line separated by space
            temp_display = "  ".join(temp_parts) if temp_parts else "N/A"
            self._draw_stat_box(stdscr, y, x_left, "GPU/CPU TEMP", temp_display)
            self._prev_gpu_temp = temp_info
        y += 2  # Back to 2 since single line now

        # VRAM (only redraw if changed)
        vram_info = (vram_used_str, vram_total_str)
        if vram_info != self._prev_vram:
            if vram_used_str and vram_total_str:
                vram_text = f"Used: {vram_used_str}\nTotal: {vram_total_str}"
                self._draw_stat_box(stdscr, y, x_left, "VRAM", vram_text)
            else:
                self._draw_stat_box(stdscr, y, x_left, "VRAM", "N/A")
            self._prev_vram = vram_info
        y += 3

        # RAM (only redraw if changed)
        ram_info = (ram_avail, ram_used)
        if ram_info != self._prev_ram:
            ram_text = f"Avail: {ram_avail} MB\nUsed: {ram_used} MB"
            self._draw_stat_box(stdscr, y, x_left, "RAM", ram_text)
            self._prev_ram = ram_info
        y += 3

        # Swap (only redraw if changed)
        swap_info = (swap_avail, swap_used)
        if swap_info != self._prev_swap:
            swap_text = f"Avail: {swap_avail} MB\nUsed: {swap_used} MB"
            self._draw_stat_box(stdscr, y, x_left, "SWAP", swap_text)
            self._prev_swap = swap_info
        y += 3

        # Top CPU Apps (only redraw if changed)
        if top_cpu != self._prev_cpu_apps:
            cpu_lines = []
            for i, (name, cpu) in enumerate(top_cpu, 1):
                cmd_short = name[:25] if len(name) <= 25 else name[:22] + "..."
                cpu_lines.append(f"{i}. {cmd_short:25} {cpu:5.1f}%")
            self._draw_stat_box(
                stdscr,
                y,
                x_left,
                "TOP CPU",
                "\n".join(cpu_lines) if cpu_lines else "No data",
            )
            self._prev_cpu_apps = top_cpu
        y += len(top_cpu) + 1  # Reduced gap

        # Top Memory Apps (only redraw if changed)
        if top_mem != self._prev_mem_apps:
            mem_lines = []
            for i, (name, mem) in enumerate(top_mem, 1):
                cmd_short = name[:25] if len(name) <= 25 else name[:22] + "..."
                mem_lines.append(f"{i}. {cmd_short:25} {mem}")
            self._draw_stat_box(
                stdscr,
                y,
                x_left,
                "TOP MEMORY",
                "\n".join(mem_lines) if mem_lines else "No data",
            )
            self._prev_mem_apps = top_mem
        y += len(top_mem) + 2

        # World Clocks - add as many as fit in remaining space
        remaining_rows = height - y  # Use all remaining space
        if remaining_rows > 0:
            # Only redraw clocks every second (they change frequently)
            import time as time_module

            current_minute = int(time_module.time() / 60)  # Change every minute
            if current_minute != self._prev_clocks:
                self._draw_world_clocks(stdscr, y, x_left, remaining_rows)
                self._prev_clocks = current_minute

        # Right column - Newsfeed (only redraw if news changed)
        news_x = x_left + left_column_width + 3  # 3 chars padding
        with self.news_lock:
            current_news = list(self.news_items)  # Make a copy for comparison

        if current_news != self._prev_news_items:
            self._draw_newsfeed(stdscr, height, width, news_x)
            self._prev_news_items = current_news

        stdscr.refresh()

    def _draw_world_clocks(self, stdscr: curses.window, y: int, x: int, max_rows: int):
        """Draw world clocks for different timezones."""
        from datetime import datetime

        # Define timezones with their UTC offsets and names
        # Format: (display_name, utc_offset_hours)
        timezones = [
            ("Local", None),  # System local time
            ("UTC", 0),
            ("Istanbul", 3),  # UTC+3 (TRT - Turkey Time)
            ("Tokyo", 9),
            ("California", -8),  # PST (UTC-8, may vary with DST)
            ("New York", -5),  # EST (UTC-5, may vary with DST)
            ("Sydney", 11),
            ("Dubai", 4),
        ]

        # Calculate how many clocks we can fit
        num_clocks = min(len(timezones), max_rows - 1)  # -1 for header

        if num_clocks <= 0:
            return

        try:
            # Draw header (Monokai-style: magenta/purple for headers)
            stdscr.addstr(
                y,
                x,
                "[WORLD CLOCKS]",
                curses.color_pair(ColorPair.MAGENTA_ON_BLACK) | curses.A_BOLD,
            )
            y += 1

            for i in range(num_clocks):
                tz_name, utc_offset = timezones[i]

                if utc_offset is None:
                    # Local time
                    now = datetime.now()
                    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # UTC-based time
                    now_utc = datetime.utcnow()
                    # Add offset
                    from datetime import timedelta

                    tz_time = now_utc + timedelta(hours=utc_offset)
                    time_str = tz_time.strftime("%Y-%m-%d %H:%M:%S")

                # Format with colors: cyan for location, bright green for time
                try:
                    # Location name in cyan
                    stdscr.addstr(
                        y,
                        x + 2,
                        f"{tz_name:10}",
                        curses.color_pair(ColorPair.CYAN_ON_BLACK),
                    )
                    # Time in bright green
                    stdscr.addstr(
                        y,
                        x + 13,
                        f"{time_str}".ljust(23),
                        curses.color_pair(ColorPair.BRIGHT_GREEN_ON_BLACK),
                    )
                except curses.error:
                    pass
                y += 1

        except Exception as e:
            self.logger.debug(f"Error drawing world clocks: {e}")

    def _draw_stat_box(
        self, stdscr: curses.window, y: int, x: int, title: str, content: str
    ):
        """Draw a small box with title and content, clearing old content."""
        try:
            # Calculate the width needed for this stat box
            box_width = 38  # Fixed width for consistent clearing

            # Title in magenta (Monokai-style)
            stdscr.addstr(
                y,
                x,
                f"[{title}]".ljust(box_width),
                curses.color_pair(ColorPair.MAGENTA_ON_BLACK) | curses.A_BOLD,
            )

            # Content - pad each line with spaces to clear old content
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                try:
                    # Parse line for label: value pattern
                    if ":" in line and not line.startswith("["):
                        # Split on first colon
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            label = parts[0] + ":"
                            value = parts[1]
                            # Label in cyan, value in bright green
                            stdscr.addstr(
                                y + i,
                                x + 2,
                                label,
                                curses.color_pair(ColorPair.CYAN_ON_BLACK),
                            )
                            stdscr.addstr(
                                y + i,
                                x + 2 + len(label),
                                value.ljust(box_width - 2 - len(label)),
                                curses.color_pair(ColorPair.BRIGHT_GREEN_ON_BLACK),
                            )
                        else:
                            # No colon, use yellow for whole line
                            padded_line = line.ljust(box_width - 2)
                            stdscr.addstr(
                                y + i,
                                x + 2,
                                padded_line,
                                curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                            )
                    else:
                        # Process list items (e.g., "1. processname 123.45%")
                        padded_line = line.ljust(box_width - 2)
                        stdscr.addstr(
                            y + i,
                            x + 2,
                            padded_line,
                            curses.color_pair(ColorPair.BRIGHT_GREEN_ON_BLACK),
                        )
                except curses.error:
                    pass
        except curses.error:
            pass

    def _format_news_item_for_kiosk(self, item: str, max_width: int) -> str:
        """Format news item to show only time (HH:MM) instead of full date-time."""
        import re

        # Pattern: [DD.MM.YYYY HH:MM] or similar
        # Replace with just [HH:MM] with zero-padded hours
        match = re.search(r"\[[\d.]+\s+(\d+):(\d+)\]", item)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            # Format with zero-padding
            time_str = f"{hour:02d}:{minute:02d}"
            # Replace the full date-time with just time
            formatted = re.sub(r"\[[\d.\s:]+\]", f"[{time_str}]", item, count=1)
            return formatted[:max_width]

        # No date pattern found, just truncate
        return item[:max_width]

    def _draw_news_item_colored(
        self,
        stdscr: curses.window,
        y: int,
        x: int,
        text: str,
        available_width: int,
        is_odd: bool,
    ):
        """Draw a news item with colored time and text (Monokai-style with striping)."""
        import re

        # Alternate colors: odd lines in white, even lines in magenta for better readability
        text_color = ColorPair.WHITE_ON_BLACK if is_odd else ColorPair.MAGENTA_ON_BLACK

        # Extract time if present: [HH:MM]
        match = re.search(r"\[(\d+:\d+)\]", text)
        if match:
            time_str = f"[{match.group(1)}]"
            # Get text after time
            rest = text[match.end() :].strip()

            try:
                # Draw bullet in yellow
                stdscr.addstr(
                    y,
                    x,
                    BoxChars.BULLET + " ",
                    curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                )
                # Draw time in cyan
                stdscr.addstr(
                    y, x + 2, time_str + " ", curses.color_pair(ColorPair.CYAN_ON_BLACK)
                )
                # Draw rest in alternating color, padded
                rest_padded = rest.ljust(available_width - len(time_str) - 3)
                stdscr.addstr(
                    y,
                    x + 2 + len(time_str) + 1,
                    rest_padded,
                    curses.color_pair(text_color),
                )
            except curses.error:
                pass
        else:
            # No time found, just draw normally
            try:
                padded_text = text.ljust(available_width)
                stdscr.addstr(
                    y,
                    x + 2,
                    BoxChars.BULLET + " ",
                    curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                )
                stdscr.addstr(y, x + 4, padded_text, curses.color_pair(text_color))
            except curses.error:
                pass

    def _draw_newsfeed(
        self, stdscr: curses.window, height: int, width: int, x_right: int
    ):
        """Draw the newsfeed on the right side."""
        available_width = width - x_right - 4  # 4 chars margin to prevent overflow
        y = 1  # Start from top row

        # Clear the entire news area first to remove old content
        for clear_y in range(y, height - 1):
            try:
                stdscr.addstr(clear_y, x_right, " " * (width - x_right - 2))
            except curses.error:
                pass

        y = 1  # Reset y position

        # Title
        try:
            stdscr.addstr(
                y,
                x_right,
                "NEWS FEED",
                curses.color_pair(ColorPair.YELLOW_ON_BLACK) | curses.A_BOLD,
            )
            stdscr.addstr(
                y,
                x_right + 12,
                "(Updates every 60s)",
                curses.color_pair(ColorPair.CYAN_ON_BLACK),
            )
        except curses.error:
            pass

        y += 2

        # Calculate how many items per source (aware of screen height)
        available_rows = height - y  # Use all remaining rows

        with self.news_lock:
            if not self.news_items:
                try:
                    stdscr.addstr(
                        y,
                        x_right,
                        "Loading news...",
                        curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                    )
                except curses.error:
                    pass
                return

            # Group by source
            sources_dict = {}
            for source, title in self.news_items:
                if source not in sources_dict:
                    sources_dict[source] = []
                sources_dict[source].append(title)

            # Calculate items per source
            num_sources = len(sources_dict)
            if num_sources > 0:
                # Account for source headers (1 line each) in calculation
                rows_for_headers = num_sources
                rows_for_items = available_rows - rows_for_headers
                items_per_source = max(1, rows_for_items // num_sources)

                for source, items in sources_dict.items():
                    if y >= height - 1:
                        break

                    # Source header in yellow (Monokai accent)
                    try:
                        stdscr.addstr(
                            y,
                            x_right,
                            f"─ {source} ─",
                            curses.color_pair(ColorPair.YELLOW_ON_BLACK)
                            | curses.A_BOLD,
                        )
                    except curses.error:
                        pass
                    y += 1

                    # Display items for this source
                    items_shown = 0
                    for item in items:
                        if y >= height - 1 or items_shown >= items_per_source:
                            break

                        # Strip date, keep only time [HH:MM] format
                        display_text = self._format_news_item_for_kiosk(
                            item, available_width
                        )
                        # Draw with colors (striped)
                        is_odd = items_shown % 2 == 0
                        self._draw_news_item_colored(
                            stdscr, y, x_right, display_text, available_width, is_odd
                        )
                        y += 1
                        items_shown += 1


# Global instance
_kiosk_mode: Optional[KioskMode] = None


def get_kiosk_mode() -> KioskMode:
    """Get the global kiosk mode instance."""
    global _kiosk_mode
    if _kiosk_mode is None:
        _kiosk_mode = KioskMode()
    return _kiosk_mode


def start_kiosk_mode():
    """Start kiosk mode background services."""
    get_kiosk_mode().start()


def stop_kiosk_mode():
    """Stop kiosk mode background services."""
    global _kiosk_mode
    if _kiosk_mode is not None:
        _kiosk_mode.stop()
        _kiosk_mode._first_draw = True  # Reset for next time


def display_kiosk_mode(stdscr: curses.window):
    """Display the kiosk mode."""
    get_kiosk_mode().display(stdscr)
