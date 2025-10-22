"""UI constants, themes, and color definitions for mytools application."""

import curses
from enum import IntEnum
from typing import Dict, Tuple


# Box drawing characters
class BoxChars:
    """Unicode box drawing characters."""

    CORNER_LEFT_UP = "┌"
    CORNER_RIGHT_UP = "┐"
    CORNER_LEFT_DOWN = "└"
    CORNER_RIGHT_DOWN = "┘"
    HORIZONTAL_LINE = "─"
    VERTICAL_LINE = "│"

    # Double-line boxes for emphasis
    DOUBLE_CORNER_LEFT_UP = "╔"
    DOUBLE_CORNER_RIGHT_UP = "╗"
    DOUBLE_CORNER_LEFT_DOWN = "╚"
    DOUBLE_CORNER_RIGHT_DOWN = "╝"
    DOUBLE_HORIZONTAL_LINE = "═"
    DOUBLE_VERTICAL_LINE = "║"

    # Mixed thick/thin
    THICK_HORIZONTAL = "━"
    THICK_VERTICAL = "┃"

    # Special characters
    BULLET = "●"
    ARROW_RIGHT = "▶"
    ARROW_DOWN = "▼"
    DIAMOND = "◆"
    SEPARATOR = "•"


class ColorPair(IntEnum):
    """Color pair constants."""

    WHITE_ON_BLACK = 1
    YELLOW_ON_BLACK = 2
    GREEN_ON_BLACK = 3
    RED_ON_BLACK = 4
    BLACK_ON_CYAN = 5
    BLACK_ON_YELLOW = 6
    BLACK_ON_RED = 7
    BLACK_ON_GREEN = 8
    CYAN_ON_BLACK = 9
    BLACK_ON_WHITE = 10
    WHITE_ON_DARK_GRAY = 11
    YELLOW_ON_DARK_GRAY = 12
    GREEN_ON_DARK_GRAY = 13
    RED_ON_DARK_GRAY = 14
    CYAN_ON_DARK_GRAY = 15
    # Enhanced UI colors
    BRIGHT_WHITE_ON_BLUE = 16
    BRIGHT_YELLOW_ON_BLUE = 17
    WHITE_ON_BLUE = 18
    BLUE_ON_BLACK = 19
    MAGENTA_ON_BLACK = 20
    BRIGHT_GREEN_ON_BLACK = 21
    BRIGHT_CYAN_ON_BLACK = 22
    BLACK_ON_MAGENTA = 23
    WHITE_ON_MAGENTA = 24


class KeyBindings:
    """Key binding constants."""

    QUIT = ord("q")
    HELP = [curses.KEY_F1, ord("?")]
    SENSORS = curses.KEY_F2
    NEWS = curses.KEY_F3
    NETWORK = curses.KEY_F4

    # Sensor view
    COMBINE_VIEW = ord("c")
    HIDE_COMMAND = ord("h")
    TOGGLE_GPU_PROCESSES = 9  # TAB key

    # News view
    REFRESH = ord("r")
    OPEN_BROWSER = [ord("o"), ord("O")]
    READ_NEWS = [curses.KEY_ENTER, 10]

    # Network view
    CLEAN_DATA = ord("c")
    HIDE_HTTP = ord("h")
    DUMP_DATA = ord("d")
    EXCLUDE_PROCESSES = ord("e")


class Theme:
    """UI theme configuration."""

    @staticmethod
    def init_colors() -> None:
        """Initialize curses color pairs."""
        if not curses.has_colors():
            return

        curses.start_color()

        # Define a dark gray color if possible
        if curses.can_change_color():
            curses.init_color(8, 200, 200, 200)  # Dark gray

        # Standard colors
        curses.init_pair(
            ColorPair.WHITE_ON_BLACK, curses.COLOR_WHITE, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.YELLOW_ON_BLACK, curses.COLOR_YELLOW, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.GREEN_ON_BLACK, curses.COLOR_GREEN, curses.COLOR_BLACK
        )
        curses.init_pair(ColorPair.RED_ON_BLACK, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(ColorPair.BLACK_ON_CYAN, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(
            ColorPair.BLACK_ON_YELLOW, curses.COLOR_BLACK, curses.COLOR_YELLOW
        )
        curses.init_pair(ColorPair.BLACK_ON_RED, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(
            ColorPair.BLACK_ON_GREEN, curses.COLOR_BLACK, curses.COLOR_GREEN
        )
        curses.init_pair(ColorPair.CYAN_ON_BLACK, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(
            ColorPair.BLACK_ON_WHITE, curses.COLOR_BLACK, curses.COLOR_WHITE
        )

        # Subtle striped colors (using dim attribute for darker background)
        curses.init_pair(
            ColorPair.WHITE_ON_DARK_GRAY, curses.COLOR_WHITE, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.YELLOW_ON_DARK_GRAY, curses.COLOR_YELLOW, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.GREEN_ON_DARK_GRAY, curses.COLOR_GREEN, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.RED_ON_DARK_GRAY, curses.COLOR_RED, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.CYAN_ON_DARK_GRAY, curses.COLOR_CYAN, curses.COLOR_BLACK
        )

        # Enhanced UI colors for modern look
        curses.init_pair(
            ColorPair.BRIGHT_WHITE_ON_BLUE, curses.COLOR_WHITE, curses.COLOR_BLUE
        )
        curses.init_pair(
            ColorPair.BRIGHT_YELLOW_ON_BLUE, curses.COLOR_YELLOW, curses.COLOR_BLUE
        )
        curses.init_pair(ColorPair.WHITE_ON_BLUE, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(ColorPair.BLUE_ON_BLACK, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(
            ColorPair.MAGENTA_ON_BLACK, curses.COLOR_MAGENTA, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.BRIGHT_GREEN_ON_BLACK, curses.COLOR_GREEN, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.BRIGHT_CYAN_ON_BLACK, curses.COLOR_CYAN, curses.COLOR_BLACK
        )
        curses.init_pair(
            ColorPair.BLACK_ON_MAGENTA, curses.COLOR_BLACK, curses.COLOR_MAGENTA
        )
        curses.init_pair(
            ColorPair.WHITE_ON_MAGENTA, curses.COLOR_WHITE, curses.COLOR_MAGENTA
        )

    @staticmethod
    def get_status_color(
        value: float, warning_threshold: float, critical_threshold: float
    ) -> ColorPair:
        """Get color based on threshold values."""
        if value > critical_threshold:
            return ColorPair.RED_ON_BLACK
        elif value > warning_threshold:
            return ColorPair.YELLOW_ON_BLACK
        else:
            return ColorPair.WHITE_ON_BLACK

    @staticmethod
    def parse_color_prefix(text: str) -> Tuple[str, ColorPair]:
        """Parse color prefix from text and return clean text with color."""
        if text.startswith("GREEN!"):
            return text[6:], ColorPair.BLACK_ON_GREEN
        elif text.startswith("RED!"):
            return text[4:], ColorPair.BLACK_ON_RED
        elif text.startswith("YELLOW!"):
            return text[7:], ColorPair.BLACK_ON_YELLOW
        else:
            return text, ColorPair.WHITE_ON_BLACK

    @staticmethod
    def get_row_color(base_color: ColorPair, row_index: int) -> Tuple[ColorPair, int]:
        """Get alternating row colors for subtle striping."""
        is_alternate_row = row_index % 2 == 1

        if is_alternate_row:
            # Use dim attribute for subtle darker background
            if base_color == ColorPair.WHITE_ON_BLACK:
                return ColorPair.WHITE_ON_DARK_GRAY, curses.A_DIM
            elif base_color == ColorPair.YELLOW_ON_BLACK:
                return ColorPair.YELLOW_ON_DARK_GRAY, curses.A_DIM
            elif base_color == ColorPair.GREEN_ON_BLACK:
                return ColorPair.GREEN_ON_DARK_GRAY, curses.A_DIM
            elif base_color == ColorPair.RED_ON_BLACK:
                return ColorPair.RED_ON_DARK_GRAY, curses.A_DIM
            elif base_color == ColorPair.CYAN_ON_BLACK:
                return ColorPair.CYAN_ON_DARK_GRAY, curses.A_DIM
            else:
                return base_color, curses.A_DIM
        else:
            return base_color, curses.A_NORMAL


class Layout:
    """Layout constants and calculations."""

    @staticmethod
    def get_help_window_size() -> Tuple[int, int]:
        """Get dimensions for help window."""
        return 17, 50

    @staticmethod
    def get_help_window_position() -> Tuple[int, int]:
        """Get position for help window."""
        return 5, 5

    @staticmethod
    def get_news_window_margins() -> Tuple[int, int]:
        """Get margins for news detail window."""
        return 20, 20  # height_margin, width_margin

    @staticmethod
    def get_news_window_position() -> Tuple[int, int]:
        """Get position for news detail window."""
        return 10, 10

    @staticmethod
    def calculate_panel_dimensions(
        screen_height: int, screen_width: int, thermal_zones_count: int
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """Calculate panel dimensions based on screen size and content."""
        # Reserve space for top menu (1 line) and status bar (1 line)
        available_height = screen_height - 2
        thermal_area_height = thermal_zones_count + 2
        cpu_area_height = available_height - thermal_area_height
        gpu_width = min(screen_width // 2 - 5, 35)

        # Reserve space for separator (1 char)
        left_panel_width = gpu_width + 1  # Reduced by 1 for separator
        separator_x = gpu_width + 1
        right_panel_x = separator_x + 1
        right_panel_width = screen_width - right_panel_x

        return {
            "gpu": (1, 0, left_panel_width, 10),  # y, x, width, height
            "cpu": (11, 0, left_panel_width, cpu_area_height - 10),  # Adjust CPU height
            "memory": (1, right_panel_x, right_panel_width, cpu_area_height // 2),
            "processes": (
                cpu_area_height // 2 + 1,
                right_panel_x,
                right_panel_width,
                cpu_area_height // 2,
            ),
            "thermal": (
                cpu_area_height + 1,
                0,
                screen_width,
                min(thermal_area_height, screen_height - cpu_area_height - 2),
            ),  # Ensure thermal doesn't overlap status bar
        }
