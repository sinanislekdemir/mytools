"""Main application entry point with refactored structure."""

import curses
import time
from threading import Thread

from .config import Config
from .logger import Logger
from .netwatch import NetworkMonitor
from .news import NewsManager
from .sensors import SensorManager
from .themes import ColorPair, KeyBindings, Layout, Theme
from mytools.core.ui import (
    draw_status_bar as core_draw_status_bar,
    draw_top_menu as core_draw_top_menu,
)


class MyToolsApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.running = False
        self.mode = "system"
        self.last_size = (0, 0)
        self.network_monitor = NetworkMonitor()
        self.news_manager = NewsManager()
        self.sensor_manager = SensorManager()
        self.logger = Logger.get_logger()

    def setup_curses(self, stdscr: curses.window) -> None:
        """Initialize curses settings."""
        stdscr.clear()
        stdscr.refresh()
        curses.curs_set(0)
        stdscr.nodelay(True)
        curses.cbreak()
        Theme.init_colors()

    def handle_screen_resize(self, stdscr: curses.window) -> bool:
        """Handle screen resize events. Returns True if screen was resized."""
        height, width = stdscr.getmaxyx()
        if (height, width) != self.last_size:
            stdscr.clear()
            self.last_size = (height, width)
            return True
        return False

    def draw_status_bar(self, stdscr: curses.window) -> None:
        """Draw the application status bar."""
        # Delegate to core UI status bar and top menu
        # core_draw_top_menu draws the top tabs; core_draw_status_bar draws the bottom bar
        core_draw_top_menu(stdscr, self.mode)
        current_time = time.strftime("%H:%M:%S")
        core_draw_status_bar(stdscr, self.mode.capitalize(), current_time)

    def show_help_window(self, stdscr: curses.window) -> None:
        """Display the help window."""
        help_height, help_width = Layout.get_help_window_size()
        help_y, help_x = Layout.get_help_window_position()

        helpwin = curses.newwin(help_height, help_width, help_y, help_x)
        helpwin.box()

        # Help content
        helpwin.addstr(1, 2, "Help", curses.color_pair(ColorPair.WHITE_ON_BLACK))
        helpwin.addstr(3, 2, "F1: Help", curses.color_pair(ColorPair.WHITE_ON_BLACK))
        helpwin.addstr(4, 2, "F2: Sensors", curses.color_pair(ColorPair.WHITE_ON_BLACK))
        helpwin.addstr(5, 2, "F3: News", curses.color_pair(ColorPair.WHITE_ON_BLACK))
        helpwin.addstr(6, 2, "F4: Network", curses.color_pair(ColorPair.WHITE_ON_BLACK))
        helpwin.addstr(7, 2, "Q: Quit", curses.color_pair(ColorPair.WHITE_ON_BLACK))

        helpwin.addstr(
            1, 14, "Sensor View:", curses.color_pair(ColorPair.YELLOW_ON_BLACK)
        )
        helpwin.addstr(
            2, 14, "C: Combined view", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )
        helpwin.addstr(
            3, 14, "H: Hide command", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )

        helpwin.addstr(
            4, 14, "News View:", curses.color_pair(ColorPair.YELLOW_ON_BLACK)
        )
        helpwin.addstr(
            5,
            14,
            "Left/Right: Change source",
            curses.color_pair(ColorPair.WHITE_ON_BLACK),
        )
        helpwin.addstr(
            6, 14, "Enter: Read news", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )
        helpwin.addstr(
            7, 14, "O: Browse news", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )

        helpwin.addstr(
            8, 14, "Network View:", curses.color_pair(ColorPair.YELLOW_ON_BLACK)
        )
        helpwin.addstr(
            9, 14, "C: Clean past data", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )
        helpwin.addstr(
            10, 14, "H: Hide HTTP", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )
        helpwin.addstr(
            11, 14, "R: Refresh", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )
        helpwin.addstr(
            12, 14, "D: Dump past data", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )

        helpwin.addstr(
            13,
            2,
            "You can edit ~/.news_sources.txt",
            curses.color_pair(ColorPair.WHITE_ON_BLACK),
        )
        helpwin.addstr(
            14,
            2,
            "to add your own news sources",
            curses.color_pair(ColorPair.WHITE_ON_BLACK),
        )
        helpwin.addnstr(
            15,
            14,
            "sinan@islekdemir.com",
            20,
            curses.color_pair(ColorPair.GREEN_ON_BLACK),
        )

        helpwin.refresh()
        helpwin.getch()  # Wait for key press

    def handle_mode_keys(self, key: int, stdscr: curses.window) -> None:
        """Handle mode switching keys."""
        if key == KeyBindings.SENSORS:
            self.mode = "system"
            stdscr.nodelay(True)
            stdscr.clear()
            stdscr.refresh()
        elif key == KeyBindings.NEWS:
            self.mode = "news"
            stdscr.nodelay(False)
            stdscr.clear()
            stdscr.refresh()
        elif key == KeyBindings.NETWORK:
            self.mode = "network"
            stdscr.nodelay(True)
            stdscr.clear()
            stdscr.refresh()

    def handle_system_mode(self, key: int, stdscr: curses.window) -> None:
        """Handle system monitoring mode."""
        if key == KeyBindings.HIDE_COMMAND:
            self.sensor_manager.switch_hide_command()
        elif key == KeyBindings.COMBINE_VIEW:
            self.sensor_manager.switch_combined()

        self.sensor_manager.display_system_info(stdscr)
        stdscr.refresh()
        time.sleep(Config.REFRESH_INTERVAL)

    def handle_network_mode(self, key: int, stdscr: curses.window) -> None:
        """Handle network monitoring mode."""
        if key == KeyBindings.CLEAN_DATA:
            self.network_monitor.clean_past_data()
        elif key == KeyBindings.HIDE_HTTP:
            self.network_monitor.toggle_hide_http()
        elif key == KeyBindings.DUMP_DATA:
            self.network_monitor.dump_past_data()

        self.network_monitor.display_network_info(stdscr)
        stdscr.refresh()
        time.sleep(Config.REFRESH_INTERVAL)

    def handle_news_mode(self, key: int, stdscr: curses.window) -> None:
        """Handle news mode."""
        self.news_manager.handle_input(stdscr, key)
        stdscr.refresh()

    def main_loop(self, stdscr: curses.window) -> None:
        """Main application loop."""
        self.setup_curses(stdscr)

        while True:
            # Handle screen resize
            self.handle_screen_resize(stdscr)

            # Get user input
            key = stdscr.getch()

            # Handle quit
            if key == KeyBindings.QUIT:
                self.running = False
                break

            # Handle help
            if key in KeyBindings.HELP:
                self.show_help_window(stdscr)

            # Handle mode switching
            self.handle_mode_keys(key, stdscr)

            # Draw status bar
            # Use centralized status bar from core.ui
            self.draw_status_bar(stdscr)

            # Handle mode-specific logic
            if self.mode == "system":
                self.handle_system_mode(key, stdscr)
            elif self.mode == "network":
                self.handle_network_mode(key, stdscr)
            elif self.mode == "news":
                self.handle_news_mode(key, stdscr)

    def network_listener_thread(self) -> None:
        """Background thread for network monitoring."""
        while self.running:
            try:
                self.network_monitor.update_network_data()
                time.sleep(Config.NETWORK_REFRESH_INTERVAL)
            except Exception as e:
                self.logger.exception(f"Network listener error: {e}")

    def run(self) -> None:
        """Start the application."""
        self.running = True

        # Start network monitoring thread
        network_thread = Thread(target=self.network_listener_thread)
        network_thread.daemon = True
        network_thread.start()

        try:
            curses.wrapper(self.main_loop)
        except Exception as e:
            self.logger.exception(f"Application error: {e}")
            raise
        finally:
            self.running = False


def main() -> None:
    """Application entry point."""
    app = MyToolsApp()
    app.run()


if __name__ == "__main__":
    main()
