"""Enhanced help system with modern UI design."""

import curses
from typing import Dict, List, Tuple

from .themes import ColorPair


class HelpSystem:
    """Modern help system with enhanced visual design."""

    def __init__(self):
        """Initialize help system."""
        self.help_content = self._build_help_content()

    def _build_help_content(self) -> Dict[str, List[Tuple[str, str]]]:
        """Build structured help content."""
        return {
            "🔧 General": [
                ("F1 or ?", "Show this help"),
                ("F2", "System sensors & processes"),
                ("F3", "News reader"),
                ("F4", "Network monitoring"),
                ("Q", "Quit application"),
            ],
            "📊 Sensors View": [
                ("C", "Toggle combined view"),
                ("H", "Hide/show command names"),
                ("TAB", "Switch CPU ⟷ GPU processes"),
                ("↑↓", "Scroll through process list"),
            ],
            "📰 News View": [
                ("←→", "Switch news sources"),
                ("↑↓", "Navigate articles"),
                ("Enter", "Read full article"),
                ("O", "Open in browser"),
                ("R", "Refresh news"),
            ],
            "🌐 Network View": [
                ("C", "Clear historical data"),
                ("H", "Hide/show HTTP traffic"),
                ("D", "Dump network data"),
                ("↑↓", "Scroll connections"),
            ],
        }

    def show_help(self, stdscr: curses.window) -> None:
        """Display the enhanced help window."""
        height, width = stdscr.getmaxyx()

        # Calculate optimal window size
        help_width = min(80, width - 4)
        help_height = min(24, height - 4)

        # Center the window
        start_y = (height - help_height) // 2
        start_x = (width - help_width) // 2

        # Create help window with shadow effect
        self._draw_shadow(stdscr, start_y + 1, start_x + 1, help_width, help_height)

        help_win = curses.newwin(help_height, help_width, start_y, start_x)
        help_win.keypad(True)

        self._draw_help_content(help_win, help_width, help_height)

        # Wait for user input
        help_win.getch()
        help_win.clear()
        help_win.refresh()
        del help_win

    def _draw_shadow(
        self, stdscr: curses.window, y: int, x: int, width: int, height: int
    ) -> None:
        """Draw a subtle shadow effect."""
        try:
            for i in range(height):
                if y + i < stdscr.getmaxyx()[0] and x + width < stdscr.getmaxyx()[1]:
                    stdscr.addch(
                        y + i,
                        x + width,
                        " ",
                        curses.color_pair(ColorPair.BLACK_ON_WHITE) | curses.A_DIM,
                    )

            for j in range(1, width + 1):
                if y + height < stdscr.getmaxyx()[0] and x + j < stdscr.getmaxyx()[1]:
                    stdscr.addch(
                        y + height,
                        x + j,
                        " ",
                        curses.color_pair(ColorPair.BLACK_ON_WHITE) | curses.A_DIM,
                    )
        except curses.error:
            pass

    def _draw_help_content(
        self, help_win: curses.window, width: int, height: int
    ) -> None:
        """Draw the help content with modern styling."""
        help_win.clear()

        # Draw border with double lines
        self._draw_fancy_border(help_win, width, height)

        # Title with gradient-like effect
        title = "📖 MyTools - Help & Shortcuts"
        title_x = (width - len(title)) // 2
        help_win.addstr(
            1,
            title_x,
            title,
            curses.A_BOLD | curses.color_pair(ColorPair.BRIGHT_YELLOW_ON_BLUE),
        )

        # Version info
        version_text = "v0.2.0"
        help_win.addstr(
            1,
            width - len(version_text) - 2,
            version_text,
            curses.color_pair(ColorPair.WHITE_ON_BLUE),
        )

        # Draw separator
        separator = "-" * (width - 4)
        help_win.addstr(2, 2, separator, curses.color_pair(ColorPair.BLUE_ON_BLACK))

        # Content sections
        row = 4
        col1_width = width // 2 - 3
        col2_start = width // 2 + 1

        sections = list(self.help_content.items())
        col1_sections = sections[:2]  # General, Sensors
        col2_sections = sections[2:]  # News, Network

        # Left column
        row = self._draw_help_column(help_win, col1_sections, 2, row, col1_width)

        # Right column
        self._draw_help_column(help_win, col2_sections, col2_start, 4, col1_width)

        # Footer
        footer_row = height - 3
        footer_text = "* Press any key to close *"
        footer_x = (width - len(footer_text)) // 2
        help_win.addstr(
            footer_row,
            footer_x,
            footer_text,
            curses.A_BLINK | curses.color_pair(ColorPair.CYAN_ON_BLACK),
        )

        help_win.refresh()

    def _draw_fancy_border(self, win: curses.window, width: int, height: int) -> None:
        """Draw an enhanced border."""
        try:
            # Use regular box drawing for better compatibility
            win.box()

            # Add some color to the border
            # Top and bottom lines
            for x in range(1, width - 1):
                win.addch(
                    0, x, curses.ACS_HLINE, curses.color_pair(ColorPair.BLUE_ON_BLACK)
                )
                win.addch(
                    height - 1,
                    x,
                    curses.ACS_HLINE,
                    curses.color_pair(ColorPair.BLUE_ON_BLACK),
                )

            # Side lines
            for y in range(1, height - 1):
                win.addch(
                    y, 0, curses.ACS_VLINE, curses.color_pair(ColorPair.BLUE_ON_BLACK)
                )
                win.addch(
                    y,
                    width - 1,
                    curses.ACS_VLINE,
                    curses.color_pair(ColorPair.BLUE_ON_BLACK),
                )

            # Corners
            win.addch(
                0, 0, curses.ACS_ULCORNER, curses.color_pair(ColorPair.BLUE_ON_BLACK)
            )
            win.addch(
                0,
                width - 1,
                curses.ACS_URCORNER,
                curses.color_pair(ColorPair.BLUE_ON_BLACK),
            )
            win.addch(
                height - 1,
                0,
                curses.ACS_LLCORNER,
                curses.color_pair(ColorPair.BLUE_ON_BLACK),
            )
            win.addch(
                height - 1,
                width - 1,
                curses.ACS_LRCORNER,
                curses.color_pair(ColorPair.BLUE_ON_BLACK),
            )

        except curses.error:
            # Fallback to simple box if fancy drawing fails
            win.box()

    def _draw_help_column(
        self,
        win: curses.window,
        sections: List[Tuple[str, List]],
        start_x: int,
        start_row: int,
        col_width: int,
    ) -> int:
        """Draw a column of help sections."""
        current_row = start_row

        for section_title, items in sections:
            # Section header
            win.addstr(
                current_row,
                start_x,
                section_title,
                curses.A_BOLD | curses.color_pair(ColorPair.GREEN_ON_BLACK),
            )
            current_row += 1

            # Section items
            for key, description in items:
                if current_row >= win.getmaxyx()[0] - 2:
                    break

                # Key in highlight color
                win.addstr(
                    current_row,
                    start_x + 2,
                    "• ",
                    curses.color_pair(ColorPair.CYAN_ON_BLACK),
                )
                win.addstr(
                    current_row,
                    start_x + 4,
                    key,
                    curses.A_BOLD | curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                )

                # Description
                desc_start = start_x + 4 + len(key) + 2
                if desc_start < start_x + col_width:
                    win.addstr(
                        current_row,
                        desc_start,
                        description[: col_width - (desc_start - start_x)],
                        curses.color_pair(ColorPair.WHITE_ON_BLACK),
                    )

                current_row += 1

            current_row += 1  # Extra spacing between sections

        return current_row


# Singleton instance
help_system = HelpSystem()
