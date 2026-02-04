"""Refactored news module with separated concerns."""

import curses
import os
from typing import List, Optional

from ..core.config import Config
from ..core.logger import Logger
from ..core.themes import ColorPair, KeyBindings, Layout, Theme
from .news_fetcher import NewsFetcher
from .news_cache import NewsCache
from .article_fetcher import ArticleFetcher


class NewsManager:
    """Manager for news functionality with separated concerns."""

    def __init__(self):
        """Initialize news manager."""
        self.logger = Logger.get_logger()
        self.news_cache = NewsCache()
        self.news_fetcher = NewsFetcher(self.news_cache)
        self.article_fetcher = ArticleFetcher()

        self.source_index = 0
        self.news_index = 0
        self.scroll_offset = 0
        self.sources = Config.get_news_sources()
        self.current_news: Optional[List[str]] = None

    def handle_input(self, stdscr: curses.window, key: int) -> None:
        """Handle news mode input and display."""
        height, width = stdscr.getmaxyx()

        # Create news area
        news_area = curses.newwin(height, width, 1, 0)

        # Load news on first access
        if self.current_news is None:
            self._load_current_source(news_area)

        # Handle navigation keys
        self._handle_navigation_keys(key, news_area)

        # Handle action keys
        self._handle_action_keys(key, stdscr, news_area, height, width)

        # Display news list
        self._display_news_list(news_area, height, width)

    def _handle_navigation_keys(self, key: int, news_area: curses.window) -> None:
        """Handle navigation key presses."""
        if key == 9:  # Tab key
            self._next_source(news_area)
        elif key == KeyBindings.REFRESH:
            self._refresh_current_source(news_area)
        elif key == curses.KEY_DOWN:
            self._navigate_down()
        elif key == curses.KEY_UP:
            self._navigate_up()
        elif key == curses.KEY_LEFT:
            self._previous_source(news_area)
        elif key == curses.KEY_RIGHT:
            self._next_source(news_area)
        elif key == curses.KEY_NPAGE:
            self._page_down(news_area.getmaxyx()[0])
        elif key == curses.KEY_PPAGE:
            self._page_up(news_area.getmaxyx()[0])

    def _handle_action_keys(
        self,
        key: int,
        stdscr: curses.window,
        news_area: curses.window,
        height: int,
        width: int,
    ) -> None:
        """Handle action key presses."""
        if key in KeyBindings.OPEN_BROWSER:
            self._open_in_browser()
        elif key in KeyBindings.READ_NEWS or key == 13:  # Also check for CR (13)
            self._show_news_detail(stdscr, height, width)

    def _next_source(self, news_area: curses.window) -> None:
        """Move to next news source."""
        self.source_index = (self.source_index + 1) % len(self.sources)
        self._load_current_source(news_area)
        self.news_index = 0
        self.scroll_offset = 0

    def _previous_source(self, news_area: curses.window) -> None:
        """Move to previous news source."""
        self.source_index = (self.source_index - 1) % len(self.sources)
        self._load_current_source(news_area)
        self.news_index = 0
        self.scroll_offset = 0

    def _refresh_current_source(self, news_area: curses.window) -> None:
        """Refresh current news source."""
        self._show_loading(news_area)
        self.current_news = self.news_fetcher.fetch_news(
            self.sources[self.source_index]
        )
        self.news_index = 0
        self.scroll_offset = 0

    def _navigate_down(self) -> None:
        """Navigate down in news list."""
        if self.current_news:
            if self.news_index < len(self.current_news) - 1:
                self.news_index += 1

    def _navigate_up(self) -> None:
        """Navigate up in news list."""
        if self.current_news:
            if self.news_index > 0:
                self.news_index -= 1

    def _page_down(self, page_size: int) -> None:
        """Navigate page down."""
        if self.current_news:
            self.news_index = min(
                len(self.current_news) - 1, self.news_index + page_size - 2
            )

    def _page_up(self, page_size: int) -> None:
        """Navigate page up."""
        self.news_index = max(0, self.news_index - (page_size - 2))

    def _load_current_source(self, news_area: curses.window) -> None:
        """Load news from current source."""
        self._show_loading(news_area)
        self.current_news = self.news_fetcher.fetch_news(
            self.sources[self.source_index]
        )

    def _show_loading(self, news_area: curses.window) -> None:
        """Show loading message."""
        news_area.clear()
        news_area.addstr(
            1, 0, "Loading news...", curses.color_pair(ColorPair.WHITE_ON_BLACK)
        )
        self._show_source_title(news_area)
        news_area.refresh()

    def _show_source_title(self, news_area: curses.window) -> None:
        """Show current source title."""
        title = f"[{self.sources[self.source_index]}]"
        news_area.addstr(
            0, 0, title, curses.A_BOLD | curses.color_pair(ColorPair.YELLOW_ON_BLACK)
        )

    def _display_news_list(
        self, news_area: curses.window, height: int, width: int
    ) -> None:
        """Display the list of news items with scrolling support."""
        news_area.clear()
        self._show_source_title(news_area)

        if self.current_news is None:
            news_area.addstr(
                1, 0, "Loading news...", curses.color_pair(ColorPair.WHITE_ON_BLACK)
            )
            news_area.refresh()
            return

        if not self.current_news:
            news_area.addstr(
                1, 0, "No news available", curses.color_pair(ColorPair.WHITE_ON_BLACK)
            )
            news_area.refresh()
            return

        # Calculate visible area
        # height is the news_area height, which starts after top menu
        # We need to account for: title row (1) + status bar (1)
        visible_lines = height - 2

        # Update scroll offset to keep selected item visible
        self._update_scroll_offset(visible_lines)

        # Calculate which items to display
        start_index = self.scroll_offset
        end_index = min(start_index + visible_lines, len(self.current_news))

        # Display visible news items with striping
        display_row = 1  # Start after title
        for list_index in range(start_index, end_index):
            news_item = self.current_news[list_index]

            # Wrap text to fit width
            wrapped_line = self._wrap_text(news_item, width - 3)[0]

            if list_index == self.news_index:
                # Highlight selected item
                news_area.addstr(
                    display_row,
                    0,
                    wrapped_line.ljust(width),
                    curses.color_pair(ColorPair.BLACK_ON_CYAN),
                )
            else:
                # Use alternating colors for subtle striping
                base_color = ColorPair.WHITE_ON_BLACK
                display_color, attributes = Theme.get_row_color(base_color, list_index)
                news_area.addstr(
                    display_row,
                    0,
                    wrapped_line.ljust(width),
                    curses.color_pair(display_color) | attributes,
                )

            display_row += 1

        # Show scroll indicator if there are more items
        self._show_scroll_indicator(news_area, height, width, visible_lines)

        news_area.refresh()

    def _update_scroll_offset(self, visible_lines: int) -> None:
        """Update scroll offset to keep selected item visible."""
        if not self.current_news:
            return

        # If selected item is above visible area, scroll up
        if self.news_index < self.scroll_offset:
            self.scroll_offset = self.news_index

        # If selected item is below visible area, scroll down
        elif self.news_index >= self.scroll_offset + visible_lines:
            self.scroll_offset = self.news_index - visible_lines + 1

        # Ensure scroll offset is within bounds
        max_scroll = max(0, len(self.current_news) - visible_lines)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        # Special case: if we're at the first item, ensure scroll offset is 0
        if self.news_index == 0:
            self.scroll_offset = 0

    def _show_scroll_indicator(
        self, news_area: curses.window, height: int, width: int, visible_lines: int
    ) -> None:
        """Show scroll indicators if there are more items."""
        if not self.current_news or len(self.current_news) <= visible_lines:
            return

        try:
            # Show scroll indicators
            indicator_col = width - 2

            # Up arrow if there are items above
            if self.scroll_offset > 0:
                news_area.addstr(
                    1, indicator_col, "↑", curses.color_pair(ColorPair.YELLOW_ON_BLACK)
                )

            # Down arrow if there are items below
            if self.scroll_offset + visible_lines < len(self.current_news):
                news_area.addstr(
                    visible_lines,
                    indicator_col,
                    "↓",
                    curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                )

            # Show position indicator (current/total)
            pos_text = f"{self.news_index + 1}/{len(self.current_news)}"
            if len(pos_text) < width // 4:
                pos_x = width - len(pos_text) - 1
                news_area.addstr(
                    height - 2,
                    pos_x,
                    pos_text,
                    curses.color_pair(ColorPair.CYAN_ON_BLACK),
                )

        except curses.error:
            pass

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to specified width."""
        lines = []
        words = text.split(" ")
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                current_line += word + " "
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "

        if current_line:
            lines.append(current_line.strip())

        return lines if lines else [""]

    def _open_in_browser(self) -> None:
        """Open current news item in browser."""
        if not self.current_news or self.news_index >= len(self.current_news):
            return

        try:
            news_title = self.current_news[self.news_index]
            link = self.news_cache.get_link(news_title)
            if link:
                os.system(f"xdg-open '{link}' > /dev/null 2>&1 &")
            else:
                self.logger.warning(f"No link found for news item: {news_title}")
        except Exception as e:
            self.logger.exception(f"Error opening browser: {e}")

    def _show_news_detail(self, stdscr: curses.window, height: int, width: int) -> None:
        """Show detailed news content in a popup with full article fetching."""
        if not self.current_news or self.news_index >= len(self.current_news):
            return

        try:
            news_title = self.current_news[self.news_index]
            link = self.news_cache.get_link(news_title)

            if not link:
                self.logger.warning(f"No link found for news item: {news_title}")
                return

            # Show loading message
            loading_win = curses.newwin(5, 50, height // 2 - 2, width // 2 - 25)
            loading_win.box()
            loading_win.addstr(
                2,
                2,
                "Fetching article content...",
                curses.color_pair(ColorPair.WHITE_ON_BLACK),
            )
            loading_win.refresh()

            # Fetch full article
            article_content = self.article_fetcher.fetch_article(link)

            # Clear loading message
            loading_win.clear()
            loading_win.refresh()
            del loading_win

            # Display article in scrollable window
            self._display_article_window(
                stdscr, article_content, news_title, width, height
            )

        except Exception as e:
            self.logger.exception(f"Error showing news detail: {e}")

    def _display_article_window(
        self, stdscr: curses.window, content: str, title: str, width: int, height: int
    ) -> None:
        """Display article content in a scrollable window."""
        margin_h, margin_w = Layout.get_news_window_margins()
        new_win_height = height - margin_h
        new_win_width = width - margin_w
        popup_y, popup_x = Layout.get_news_window_position()

        news_window = curses.newwin(new_win_height, new_win_width, popup_y, popup_x)
        news_window.keypad(True)
        news_window.box()

        # Create scrollable text area
        text_height = new_win_height - 4
        text_width = new_win_width - 4

        # Wrap content lines
        content_lines = []
        for line in content.split("\n"):
            if len(line) == 0:
                content_lines.append("")
            elif len(line) <= text_width:
                content_lines.append(line)
            else:
                # Wrap long lines
                wrapped = self._wrap_text(line, text_width)
                content_lines.extend(wrapped)

        scroll_pos = 0
        max_scroll = max(0, len(content_lines) - text_height)
        title = f"[ {title} ]"
        while True:
            news_window.clear()
            news_window.box()
            # Display title
            truncated_title = (
                title[: new_win_width - 4] if len(title) > new_win_width - 4 else title
            )
            news_window.addstr(
                0, 2, truncated_title, curses.color_pair(ColorPair.YELLOW_ON_BLACK)
            )

            # Display help text at bottom
            help_text = "[PgUp/PgDn/↑↓: Scroll] [o: Open in browser] [q/ESC: Close]"
            if len(help_text) < new_win_width - 4:
                news_window.addstr(
                    new_win_height - 1,
                    2,
                    help_text,
                    curses.color_pair(ColorPair.CYAN_ON_BLACK),
                )

            # Display visible content lines
            for i in range(text_height):
                line_idx = scroll_pos + i
                if line_idx < len(content_lines):
                    line = content_lines[line_idx]
                    try:
                        news_window.addstr(i + 2, 2, line[:text_width])
                    except curses.error:
                        pass  # Ignore if line is too long for window

            # Display scroll indicator
            if max_scroll > 0:
                scroll_percent = int((scroll_pos / max_scroll) * 100)
                indicator = f" {scroll_percent}% "
                news_window.addstr(
                    new_win_height - 1,
                    new_win_width - len(indicator) - 2,
                    indicator,
                    curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                )

            news_window.refresh()

            # Handle input
            key = news_window.getch()

            if key == ord("q") or key == 27:  # q or ESC
                break
            elif key in KeyBindings.OPEN_BROWSER:  # 'o' or 'O'
                self._open_in_browser()
            elif key == curses.KEY_NPAGE:  # Page Down
                scroll_pos = min(scroll_pos + text_height, max_scroll)
            elif key == curses.KEY_PPAGE:  # Page Up
                scroll_pos = max(scroll_pos - text_height, 0)
            elif key == curses.KEY_DOWN:
                scroll_pos = min(scroll_pos + 1, max_scroll)
            elif key == curses.KEY_UP:
                scroll_pos = max(scroll_pos - 1, 0)
            elif key == curses.KEY_HOME:
                scroll_pos = 0
            elif key == curses.KEY_END:
                scroll_pos = max_scroll


# Legacy function for backward compatibility
def news_loop(stdscr: curses.window, key: int):
    """Legacy news loop function."""
    # This would need to be updated to use a global NewsManager instance
    # For now, keeping it simple
    pass
