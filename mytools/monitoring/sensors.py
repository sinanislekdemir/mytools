# Refactored sensors module using modular components
import curses
import os
import signal

from mytools.core.ui import draw_panel, draw_panel_with_scrolling
from ..core.themes import Layout
from .cpu_monitor import CPUMonitor
from .process_monitor import ProcessMonitor
from .system_monitor import GPUMonitor, MemoryMonitor
from .temperature_monitor import TemperatureMonitor


class SensorManager:
    """Manager for all sensor monitoring functionality."""

    def __init__(self):
        """Initialize sensor manager with all monitors."""
        self.combined = False
        self.hide_command = False
        self.show_gpu_processes = False  # Toggle between CPU and GPU processes

        # Panel navigation and scrolling
        self.active_panel = 0  # 0=memory, 1=processes, 2=thermal
        self.scroll_offsets = [0, 0, 0]  # Scroll offset for each scrollable panel
        self.selected_lines = [0, 0, 0]  # Selected line in each panel (0 = first data row, excluding header)
        self.panel_names = ["Memory", "Processes", "Thermal"]

        self.cpu_monitor = CPUMonitor()
        self.process_monitor = ProcessMonitor()
        self.gpu_monitor = GPUMonitor()
        self.memory_monitor = MemoryMonitor()
        self.temperature_monitor = TemperatureMonitor()

    def switch_combined(self):
        """Toggle combined process view."""
        self.combined = not self.combined

    def switch_hide_command(self):
        """Toggle hiding command names in process view."""
        self.hide_command = not self.hide_command

    def toggle_gpu_processes(self):
        """Toggle between CPU processes and GPU processes view."""
        self.show_gpu_processes = not self.show_gpu_processes

    def cycle_active_panel(self):
        """Cycle through the active panels (Memory -> Processes -> Thermal if available)."""
        thermal_zones_count = len(self.temperature_monitor.get_thermal_zones())
        max_panel = (
            3 if thermal_zones_count > 0 else 2
        )  # Only cycle to thermal if it exists
        self.active_panel = (self.active_panel + 1) % max_panel

    def scroll_active_panel(self, direction: int):
        """Scroll the active panel up (-1) or down (1)."""
        if 0 <= self.active_panel < len(self.scroll_offsets):
            # Get the current data to determine bounds
            max_items = self._get_panel_item_count(self.active_panel)
            if max_items <= 0:
                return

            # Move the selected line
            old_selected = self.selected_lines[self.active_panel]
            self.selected_lines[self.active_panel] += direction

            # Bound the selected line to available data
            # selected_lines uses 0-based indexing for data rows (header is excluded)
            min_line = 0
            self.selected_lines[self.active_panel] = max(
                min_line, min(self.selected_lines[self.active_panel], max_items - 1)
            )

            # Only proceed if selection actually changed
            if self.selected_lines[self.active_panel] == old_selected:
                return

            # Auto-scroll the panel if needed
            panel_height = (
                8  # Approximate visible lines in a panel (reduced for better fit)
            )
            current_scroll = self.scroll_offsets[self.active_panel]
            selected_line = self.selected_lines[self.active_panel]

            # If selected line is above visible area, scroll up
            if selected_line < current_scroll:
                self.scroll_offsets[self.active_panel] = selected_line
            # If selected line is below visible area, scroll down
            elif selected_line >= current_scroll + panel_height:
                self.scroll_offsets[self.active_panel] = (
                    selected_line - panel_height + 1
                )

            # Ensure scroll doesn't go negative or past available data
            max_scroll = max(0, max_items - panel_height)
            self.scroll_offsets[self.active_panel] = max(
                0, min(self.scroll_offsets[self.active_panel], max_scroll)
            )

    def _get_panel_item_count(self, panel_index: int) -> int:
        """Get the number of items in the specified panel."""
        try:
            if panel_index == 0:  # Memory panel
                processes = self.process_monitor.get_processes(
                    50, "-rss", self.combined, self.hide_command
                )
                return len(processes)
            elif panel_index == 1:  # Processes panel
                if self.show_gpu_processes:
                    gpu_processes = self.gpu_monitor.get_gpu_processes(50)
                    return len(gpu_processes)
                else:
                    cpu_processes = self.process_monitor.get_processes(
                        50, "-%cpu", self.combined, self.hide_command
                    )
                    return len(cpu_processes)
            elif panel_index == 2:  # Thermal panel
                thermal_data = self.temperature_monitor.get_all_thermal_data()
                return len(thermal_data)
        except Exception:
            return 0
        return 0

    def display_system_info(self, stdscr: curses.window) -> None:
        """Display all system information panels."""
        height, width = stdscr.getmaxyx()
        thermal_zones_count = len(self.temperature_monitor.get_thermal_zones())

        # Calculate panel dimensions
        panels = Layout.calculate_panel_dimensions(height, width, thermal_zones_count)

        # GPU panel (if available)
        gpu_data = self.gpu_monitor.get_nvidia_info(panels["gpu"][2] - 2)
        if "Error" not in gpu_data:
            draw_panel(stdscr, "GPU", gpu_data, *panels["gpu"])
            cpu_panel = panels["cpu"]
        else:
            # Use the GPU space for CPU if no GPU available
            cpu_panel = (1, 0, panels["gpu"][2], height - (thermal_zones_count + 2) - 1)

        # CPU usage panel
        cpu_data = self.cpu_monitor.get_cpu_usage_data()
        draw_panel(stdscr, "CPU Usage", cpu_data, *cpu_panel)

        # Memory panel with scrolling (panel 0)
        memory_data = self.memory_monitor.get_memory_info()
        memory_processes = self.process_monitor.get_processes(
            50,
            "-rss",
            self.combined,
            self.hide_command,  # Show up to 50 processes
        )
        # Create combined data dict that can handle both strings and lists
        combined_memory_data = {}
        combined_memory_data.update(memory_data)
        combined_memory_data["Top processes"] = memory_processes
        draw_panel_with_scrolling(
            stdscr,
            "Memory",
            combined_memory_data,
            *panels["memory"],
            scroll_offset=self.scroll_offsets[0],
            is_active=(self.active_panel == 0),
            selected_line=self.selected_lines[0],
        )

        # CPU/GPU processes panel with scrolling (panel 1)
        if self.show_gpu_processes:
            gpu_processes_data = {
                "GPU Processes": self.gpu_monitor.get_gpu_processes(50)
            }
            panel_title = "GPU Processes [G: CPU]"
        else:
            cpu_processes_data = {
                "Top processes": self.process_monitor.get_processes(
                    50,
                    "-%cpu",
                    self.combined,
                    self.hide_command,  # Show up to 50 processes
                )
            }
            gpu_processes_data = cpu_processes_data
            panel_title = "CPU Processes [G: GPU]"

        draw_panel_with_scrolling(
            stdscr,
            panel_title,
            gpu_processes_data,
            *panels["processes"],
            scroll_offset=self.scroll_offsets[1],
            is_active=(self.active_panel == 1),
            selected_line=self.selected_lines[1],
        )

        # Thermal zones panel with scrolling (panel 2)
        if thermal_zones_count > 0:
            thermal_data = self.temperature_monitor.get_all_thermal_data()
            draw_panel_with_scrolling(
                stdscr,
                "Thermal zones",
                thermal_data,
                *panels["thermal"],
                scroll_offset=self.scroll_offsets[2],
                is_active=(self.active_panel == 2),
                selected_line=self.selected_lines[2],
            )

    def get_selected_process_pid(self) -> tuple[int | None, str]:
        """Get the PID of the currently selected process. Returns (pid, panel_name)."""
        from mytools.core.logger import Logger
        logger = Logger.get_logger()
        
        try:
            if self.active_panel == 0:
                processes = self.process_monitor.get_processes(
                    50, "-rss", self.combined, self.hide_command
                )
                selected_idx = self.selected_lines[0]
                # selected_idx is 0-based for data rows (excluding header)
                # so actual index in processes array is selected_idx + 1
                actual_idx = selected_idx + 1
                if actual_idx < len(processes):
                    process_row = processes[actual_idx]
                    if len(process_row) >= 1:
                        # PID is in column 0, but may have color prefix (e.g. "RED!123" or "YELLOW!456")
                        pid_str = process_row[0]
                        if '!' in pid_str:
                            pid_str = pid_str.split('!', 1)[1]
                        pid = int(pid_str)
                        return pid, "Memory"
            elif self.active_panel == 1:
                if self.show_gpu_processes:
                    gpu_processes = self.gpu_monitor.get_gpu_processes(50)
                    selected_idx = self.selected_lines[1]
                    # selected_idx is 0-based for data rows (excluding header)
                    # so actual index in processes array is selected_idx + 1
                    actual_idx = selected_idx + 1
                    if actual_idx < len(gpu_processes):
                        process_row = gpu_processes[actual_idx]
                        if len(process_row) >= 1:
                            # PID is in column 0, but may have color prefix (e.g. "RED!123" or "YELLOW!456")
                            pid_str = process_row[0]
                            if '!' in pid_str:
                                pid_str = pid_str.split('!', 1)[1]
                            pid = int(pid_str)
                            return pid, "GPU Processes"
                else:
                    cpu_processes = self.process_monitor.get_processes(
                        50, "-%cpu", self.combined, self.hide_command
                    )
                    selected_idx = self.selected_lines[1]
                    # selected_idx is 0-based for data rows (excluding header)
                    # so actual index in processes array is selected_idx + 1
                    actual_idx = selected_idx + 1
                    if actual_idx < len(cpu_processes):
                        process_row = cpu_processes[actual_idx]
                        if len(process_row) >= 1:
                            # PID is in column 0, but may have color prefix (e.g. "RED!123" or "YELLOW!456")
                            pid_str = process_row[0]
                            if '!' in pid_str:
                                pid_str = pid_str.split('!', 1)[1]
                            pid = int(pid_str)
                            return pid, "CPU Processes"
        except (ValueError, IndexError, Exception) as e:
            logger.error(f"Error getting process PID: {e}")
        
        return None, ""

    def kill_selected_process(self) -> tuple[bool, str]:
        """Kill the currently selected process with signal -9. Returns (success, message)."""
        pid, panel_name = self.get_selected_process_pid()
        if pid is None:
            return False, "No process selected"
        
        try:
            os.kill(pid, signal.SIGKILL)
            return True, f"Successfully killed process {pid} from {panel_name}"
        except ProcessLookupError:
            return False, f"Process {pid} does not exist"
        except PermissionError:
            return False, f"Permission denied to kill process {pid}"
        except Exception as e:
            return False, f"Error killing process {pid}: {str(e)}"


# Legacy functions for backward compatibility
combined = False
hide_command = False
_sensor_manager = None


def get_sensor_manager():
    """Get or create sensor manager instance."""
    global _sensor_manager
    if _sensor_manager is None:
        _sensor_manager = SensorManager()
    return _sensor_manager


def switch_combined():
    """Legacy function for combined mode toggle."""
    global combined
    combined = not combined
    get_sensor_manager().combined = combined


def switch_hide_command():
    """Legacy function for hide command toggle."""
    global hide_command
    hide_command = not hide_command
    get_sensor_manager().hide_command = hide_command


def system_loop(stdscr: curses.window):
    """Legacy function for system display loop."""
    manager = get_sensor_manager()
    manager.combined = combined
    manager.hide_command = hide_command
    manager.display_system_info(stdscr)
