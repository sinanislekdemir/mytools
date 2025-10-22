"""Legacy main module - will be replaced by app.py"""

import curses
import time
from threading import Thread

from mytools.monitoring.netwatch import (
    clean_past_data,
    dump_past_data,
    get_ss_tnp_output,
    network_loop,
    toggle_hide_http,
)
from mytools.monitoring.news_manager import NewsManager
from mytools.monitoring.sensors import switch_combined, switch_hide_command, system_loop
from mytools.core.themes import Theme, Layout
from mytools.core.help_system import help_system
from mytools.core.ui import draw_status_bar, draw_top_menu, draw_vertical_separator

# Initialize news manager
_news_manager = NewsManager()

running = False


class BackgroundMonitor:
    """Background thread for system monitoring to keep UI responsive."""

    def __init__(self):
        self.running = False
        self.thread = None
        self.last_basic_update = 0
        self.last_process_update = 0
        self.basic_interval = 1.0  # GPU/CPU usage every second
        self.process_interval = 1.0  # Process lists every second

    def start(self):
        """Start the background monitoring thread."""
        self.running = True
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the background monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join()

    def _monitor_loop(self):
        """Background monitoring loop that updates sensor data at different frequencies."""
        while self.running:
            try:
                current_time = time.time()

                # Update basic monitors (GPU/CPU usage) every 2 seconds
                if current_time - self.last_basic_update >= self.basic_interval:
                    from mytools.monitoring.sensors import get_sensor_manager

                    manager = get_sensor_manager()
                    # Force refresh of basic monitoring data
                    manager.gpu_monitor.get_nvidia_info(10)
                    manager.cpu_monitor.get_cpu_usage_data()
                    manager.memory_monitor.get_memory_info()
                    manager.temperature_monitor.get_all_thermal_data()
                    self.last_basic_update = current_time

                # Update process lists every second for responsive scrolling
                if current_time - self.last_process_update >= self.process_interval:
                    from mytools.monitoring.sensors import get_sensor_manager

                    manager = get_sensor_manager()
                    # Force refresh of process data
                    manager.process_monitor.get_processes(
                        20, "-rss", manager.combined, manager.hide_command
                    )
                    manager.process_monitor.get_processes(
                        20, "-%cpu", manager.combined, manager.hide_command
                    )
                    manager.gpu_monitor.get_gpu_processes(20)
                    self.last_process_update = current_time

                time.sleep(0.1)  # Small sleep to prevent excessive CPU usage
            except Exception as e:
                # Log error but continue monitoring
                from mytools.core.logger import Logger

                Logger.get_logger().error(f"Background monitor error: {e}")
                time.sleep(0.5)


# Global background monitor
_background_monitor = BackgroundMonitor()


def main_loop(stdscr: curses.window):
    global running, _background_monitor

    stdscr.clear()
    stdscr.refresh()
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.cbreak()
    Theme.init_colors()

    # Start background monitoring for responsive UI
    _background_monitor.start()

    last_size = (0, 0)

    mode = "system"

    while True:
        # get screen size
        height, width = stdscr.getmaxyx()
        if (height, width) != last_size:
            stdscr.clear()
            last_size = (height, width)

        key = stdscr.getch()
        
        # Debug logging
        if key != -1:
            from mytools.core.logger import Logger
            logger = Logger.get_logger()
            logger.debug(f"Key pressed: {key} (chr={chr(key) if 32 <= key < 127 else 'N/A'}) mode={mode}")
        
        if key == ord("q"):
            running = False
            _background_monitor.stop()
            break

        if key == curses.KEY_F1 or key == ord("?"):
            help_system.show_help(stdscr)

        if key == curses.KEY_F2:
            mode = "system"
            stdscr.nodelay(True)
            stdscr.clear()
            stdscr.refresh()

        if key == curses.KEY_F3:
            mode = "news"
            stdscr.nodelay(False)
            stdscr.clear()
            stdscr.refresh()

        if key == curses.KEY_F4:
            mode = "network"
            stdscr.nodelay(True)
            stdscr.clear()
            stdscr.refresh()

        # Draw top menu first
        draw_top_menu(stdscr, mode)

        if mode == "system":
            # Handle navigation keys immediately for instant response
            navigation_key_handled = False
            if key == curses.KEY_UP:  # Arrow up for scrolling
                from mytools.monitoring.sensors import get_sensor_manager

                get_sensor_manager().scroll_active_panel(-1)
                navigation_key_handled = True
            elif key == curses.KEY_DOWN:  # Arrow down for scrolling
                from mytools.monitoring.sensors import get_sensor_manager

                get_sensor_manager().scroll_active_panel(1)
                navigation_key_handled = True
            elif key == 9:  # TAB key for panel navigation
                from mytools.monitoring.sensors import get_sensor_manager

                get_sensor_manager().cycle_active_panel()
                navigation_key_handled = True

            # Handle other keys
            other_key_handled = False
            if key == ord("h"):
                switch_hide_command()
                other_key_handled = True
            elif key == ord("c"):
                switch_combined()
                other_key_handled = True
            elif key == ord("g") or key == ord("G"):  # G key for GPU/CPU toggle
                from mytools.monitoring.sensors import get_sensor_manager

                get_sensor_manager().toggle_gpu_processes()
                other_key_handled = True
            elif key == ord("k") or key == ord("K"):  # K key to kill process
                from mytools.monitoring.sensors import get_sensor_manager
                from mytools.core.ui import show_confirmation_modal
                
                sensor_mgr = get_sensor_manager()
                pid, panel_name = sensor_mgr.get_selected_process_pid()
                
                if pid is not None:
                    message = f"Kill process {pid} from {panel_name}?"
                    if show_confirmation_modal(stdscr, message):
                        success, msg = sensor_mgr.kill_selected_process()
                        stdscr.clear()
                other_key_handled = True

            # Update display (background monitor provides updated data)
            system_loop(stdscr)

            # Draw separator after all panels to prevent flickering
            height, width = stdscr.getmaxyx()
            from mytools.monitoring.sensors import get_sensor_manager

            thermal_zones_count = len(
                get_sensor_manager().temperature_monitor.get_thermal_zones()
            )
            panels = Layout.calculate_panel_dimensions(
                height, width, thermal_zones_count
            )
            separator_x = panels["gpu"][
                2
            ]  # Right edge of left panels (now properly sized)
            draw_vertical_separator(stdscr, separator_x, 1, height - 2)

            # Draw status bar AFTER all panels to ensure it's not overwritten
            current_time = time.strftime("%H:%M:%S")
            draw_status_bar(stdscr, mode.capitalize(), current_time)

            stdscr.refresh()

            # Much faster response for navigation, moderate for others
            if navigation_key_handled:
                time.sleep(0.01)  # Almost instant for scrolling/navigation
            elif other_key_handled:
                time.sleep(0.05)  # Quick for other keys
            else:
                time.sleep(0.1)  # Faster regular refresh for smooth scrolling

        if mode == "network":
            # Handle network navigation keys immediately for instant response
            network_navigation_handled = False
            if key == curses.KEY_UP:  # Arrow up for scrolling
                from mytools.monitoring.netwatch import get_network_monitor

                get_network_monitor().scroll_network(-1)
                network_navigation_handled = True
            elif key == curses.KEY_DOWN:  # Arrow down for scrolling
                from mytools.monitoring.netwatch import get_network_monitor

                get_network_monitor().scroll_network(1)
                network_navigation_handled = True

            # Handle other network keys
            network_other_handled = False
            if key == ord("c"):
                clean_past_data()
                network_other_handled = True
            elif key == ord("h"):
                toggle_hide_http()
                network_other_handled = True
            elif key == ord("d"):
                dump_past_data()
                network_other_handled = True
            elif key == ord("e"):  # Edit excluded processes
                from mytools.core.ui import show_excluded_processes_editor
                from mytools.core.config import Config

                current_excluded = Config.get_excluded_processes()
                new_excluded = show_excluded_processes_editor(stdscr, current_excluded)
                Config.set_excluded_processes(new_excluded)
                network_other_handled = True

            network_loop(stdscr)

            # Draw status bar AFTER all network panels
            current_time = time.strftime("%H:%M:%S")
            draw_status_bar(stdscr, mode.capitalize(), current_time)

            stdscr.refresh()

            # Responsive timing for network mode
            if network_navigation_handled:
                time.sleep(0.01)  # Almost instant for scrolling
            elif network_other_handled:
                time.sleep(0.05)  # Quick for other keys
            else:
                time.sleep(0.2)  # Regular refresh for network updates

        elif mode == "news":
            _news_manager.handle_input(stdscr, key)

            # Draw status bar AFTER news content
            current_time = time.strftime("%H:%M:%S")
            draw_status_bar(stdscr, mode.capitalize(), current_time)

            stdscr.refresh()


def network_listener():
    while running:
        try:
            get_ss_tnp_output()
            time.sleep(0.5)
        except Exception as e:
            with open("/tmp/err.log", "a+") as f:
                f.write(f"{time.ctime()} {e}\n")


def main():
    global running
    running = True
    t = Thread(target=network_listener)
    t.start()
    curses.wrapper(main_loop)


if __name__ == "__main__":
    """Start network listener thread."""
    main()
