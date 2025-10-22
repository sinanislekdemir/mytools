"""UI utilities with improved error handling and theming."""

import curses

from .logger import Logger
from .themes import BoxChars, ColorPair, Theme

# Deprecated - keeping for backward compatibility
CORNER_LEFT_UP = BoxChars.CORNER_LEFT_UP
CORNER_RIGHT_UP = BoxChars.CORNER_RIGHT_UP
CORNER_LEFT_DOWN = BoxChars.CORNER_LEFT_DOWN
CORNER_RIGHT_DOWN = BoxChars.CORNER_RIGHT_DOWN
HORIZONTAL_LINE = BoxChars.HORIZONTAL_LINE
VERTICAL_LINE = BoxChars.VERTICAL_LINE


def draw_panel(
    stdscr: curses.window, title: str, data: dict, y: int, x: int, w: int, h: int
):
    """Draw a panel with a title and data in a box with improved error handling."""
    logger = Logger.get_logger()

    try:
        panel_area = curses.newwin(h, w, y, x)
        panel_area.keypad(True)
        panel_area.nodelay(True)
        panel_area.scrollok(True)
        panel_area.timeout(1000)

        # Draw enhanced title bar with gradient-like effect
        title_text = f" * {title} * "
        padding = max(0, w - len(title_text))
        left_pad = padding // 2
        right_pad = padding - left_pad

        full_title = " " * left_pad + title_text + " " * right_pad
        panel_area.addstr(
            0,
            0,
            full_title,
            curses.A_BOLD | curses.color_pair(ColorPair.BRIGHT_WHITE_ON_BLUE),
        )

        text_area_height = h
        text_area_width = w - 2
        row = 1

        for key, value in data.items():
            if row >= text_area_height:
                break

            if isinstance(value, list):
                # Handle tabular data
                row = _draw_tabular_data(
                    panel_area, key, value, row, text_area_width, text_area_height
                )
            else:
                # Handle simple key-value pairs
                row = _draw_simple_data(panel_area, key, value, row, text_area_width)

        panel_area.refresh()

    except Exception as e:
        logger.exception(f"Error drawing panel '{title}': {e}")


def _draw_tabular_data(
    panel_area: curses.window,
    key: str,
    value: list,
    row: int,
    text_area_width: int,
    text_area_height: int,
) -> int:
    """Draw tabular data within a panel."""
    try:
        panel_area.addstr(
            row, 0, f"{key}:", curses.color_pair(ColorPair.YELLOW_ON_BLACK)
        )
        row += 1

        if not value:
            return row

        # Calculate column widths
        col_widths = []
        for i in range(len(value[0])):
            col_widths.append(max(len(str(value[j][i])) for j in range(len(value))))

        # Distribute extra space
        if sum(col_widths) < text_area_width:
            diff = text_area_width - sum(col_widths)
            add_per_col = diff // len(col_widths) if col_widths else 0
            for i in range(len(col_widths)):
                col_widths[i] += add_per_col

        # Draw rows with alternating colors for striping
        for line_index, line in enumerate(value):
            if row >= text_area_height:
                break

            # Parse color information and create formatted string
            formatted_line = []
            base_color = ColorPair.WHITE_ON_BLACK

            for i, cell in enumerate(line):
                cell_text, cell_color = Theme.parse_color_prefix(str(cell))
                if cell_color != ColorPair.WHITE_ON_BLACK:
                    base_color = cell_color

                # Pad cell to column width
                if i < len(col_widths):
                    formatted_line.append(cell_text.ljust(col_widths[i]))
                else:
                    formatted_line.append(cell_text)

            str_to_print = " ".join(formatted_line)
            if len(str_to_print) > text_area_width:
                str_to_print = str_to_print[: text_area_width - 3] + "..."

            # Get alternating row color for subtle striping
            display_color, attributes = Theme.get_row_color(base_color, line_index)

            # Fill the entire row width with the background color for striping effect
            str_to_print = str_to_print.ljust(text_area_width)

            panel_area.addstr(
                row, 0, str_to_print, curses.color_pair(display_color) | attributes
            )
            row += 1

        return row

    except Exception as e:
        Logger.log_warning(f"Error drawing tabular data: {e}")
        return row


def draw_status_bar(stdscr: curses.window, mode: str, extra_info: str = "") -> None:
    """Draw an enhanced status bar with mode-specific shortcuts."""
    logger = Logger.get_logger()

    try:
        height, width = stdscr.getmaxyx()
        status_y = height - 1

        # Validate basic dimensions
        if status_y < 0 or width <= 0:
            return

            # Mode-specific shortcuts (keep them short)
        mode_shortcuts = {
            "System": "↑↓:Scroll TAB:Panel K:Kill Q:Quit",
            "News": "↑↓:Scroll ENTER:Read S:Switch Q:Back",
            "Network": "↑↓:Scroll C:Clear D:Dump H:Hide E:Filter",
        }

        # Get mode-specific shortcuts
        shortcuts = mode_shortcuts.get(mode, "F1:Help F2:Sensors Q:Quit")

        # Reserve space for time info (if any)
        time_space = len(extra_info) + 3 if extra_info else 0
        available_width = max(10, width - time_space - 2)

        # Create status text - keep it short
        left_text = f" {mode}: {shortcuts}"

        # Aggressive truncation to fit safely
        if len(left_text) > available_width:
            # Try shorter version
            left_text = f" {mode}: Q:Quit"
            if len(left_text) > available_width:
                left_text = f" {mode}"

        # Final safety check - never exceed available space
        left_text = left_text[:available_width]

        try:
            # Method 1: Fill entire line with blue background first
            blank_line = " " * (
                width - 1
            )  # Fill entire width except last char to avoid cursor wrap
            stdscr.addnstr(
                status_y,
                0,
                blank_line,
                width - 1,
                curses.color_pair(ColorPair.BRIGHT_YELLOW_ON_BLUE),
            )

            # Draw the main status text with consistent blue background and yellow text
            if left_text and len(left_text) > 0:
                safe_len = min(len(left_text), width - 2)
                stdscr.addnstr(
                    status_y,
                    0,
                    left_text,
                    safe_len,
                    curses.color_pair(ColorPair.BRIGHT_YELLOW_ON_BLUE),
                )

            # Draw time info on the right if there's space
            if extra_info and len(extra_info) > 0 and width > 30:
                right_text = f" {extra_info} "
                right_len = min(len(right_text), width // 4)
                right_x = max(0, width - right_len - 1)

                if right_x > len(left_text) + 2:  # Ensure no overlap
                    stdscr.addnstr(
                        status_y,
                        right_x,
                        right_text,
                        right_len,
                        curses.color_pair(ColorPair.BRIGHT_YELLOW_ON_BLUE),
                    )

        except curses.error as e:
            # Ultra-simple fallback - just draw basic text
            logger.error(f"Status drawing failed, using fallback: {e}")
            try:
                simple_text = f" {mode} "
                stdscr.addnstr(
                    height - 1,
                    0,
                    simple_text,
                    min(len(simple_text), width - 1),
                    curses.color_pair(ColorPair.BRIGHT_YELLOW_ON_BLUE),
                )
            except curses.error:
                pass  # Give up gracefully if even this fails

    except Exception as e:
        logger.error(f"Status bar error: {e}")
        # Don't let status bar issues crash the application


def draw_vertical_separator(
    stdscr: curses.window, x: int, start_y: int, end_y: int
) -> None:
    """Draw a vertical block separator."""
    try:
        for y in range(start_y, end_y):
            if y < stdscr.getmaxyx()[0] and x < stdscr.getmaxyx()[1]:
                # Use a solid block character with blue background to create a visible separator
                stdscr.addch(y, x, "█", curses.color_pair(ColorPair.BLUE_ON_BLACK))
    except curses.error as e:
        logger = Logger.get_logger()
        logger.error(f"Failed to draw vertical separator at x={x}: {e}")


def show_excluded_processes_editor(
    stdscr: curses.window, current_keywords: list
) -> list:
    """Show dialog to edit excluded process keywords."""

    height, width = stdscr.getmaxyx()
    dialog_height = 7
    dialog_width = min(60, width - 4)
    start_y = (height - dialog_height) // 2
    start_x = (width - dialog_width) // 2

    # Create dialog window
    dialog = curses.newwin(dialog_height, dialog_width, start_y, start_x)
    dialog.box()

    # Title
    title = " Exclude Process Keywords "
    dialog.addstr(0, (dialog_width - len(title)) // 2, title, curses.A_BOLD)

    # Instructions
    dialog.addstr(2, 2, "Enter keywords separated by commas:")
    dialog.addstr(3, 2, "(Processes containing these words will be hidden)")

    # Current keywords as comma-separated string
    keywords_text = ", ".join(current_keywords)

    # Input field
    input_y = 4
    input_x = 2
    input_width = dialog_width - 4

    dialog.addstr(input_y, input_x, "Keywords: ")
    input_start_x = input_x + len("Keywords: ")

    # Draw input box
    for i in range(input_width - len("Keywords: ") - 2):
        dialog.addch(input_y, input_start_x + i, " ", curses.A_REVERSE)

    dialog.addstr(5, 2, "Press ENTER to save, ESC to cancel")
    dialog.refresh()

    # Input handling
    curses.curs_set(1)  # Show cursor
    edit_text = keywords_text
    cursor_pos = len(edit_text)

    try:
        while True:
            # Display current text
            display_text = edit_text[: input_width - len("Keywords: ") - 2]
            if len(edit_text) > len(display_text):
                display_text = "..." + edit_text[-(len(display_text) - 3) :]

            # Clear input area
            for i in range(input_width - len("Keywords: ") - 2):
                dialog.addch(input_y, input_start_x + i, " ", curses.A_REVERSE)

            # Show text
            dialog.addstr(input_y, input_start_x, display_text, curses.A_REVERSE)
            dialog.refresh()

            key = dialog.getch()

            if key == 27:  # ESC
                return current_keywords  # Cancel
            elif key in [curses.KEY_ENTER, 10, 13]:  # ENTER
                # Parse and return keywords
                if edit_text.strip():
                    keywords = [k.strip() for k in edit_text.split(",") if k.strip()]
                    return keywords
                else:
                    return []
            elif key == curses.KEY_BACKSPACE or key == 127:
                if cursor_pos > 0:
                    edit_text = edit_text[: cursor_pos - 1] + edit_text[cursor_pos:]
                    cursor_pos -= 1
            elif key >= 32 and key <= 126:  # Printable characters
                edit_text = edit_text[:cursor_pos] + chr(key) + edit_text[cursor_pos:]
                cursor_pos += 1
            elif key == curses.KEY_LEFT and cursor_pos > 0:
                cursor_pos -= 1
            elif key == curses.KEY_RIGHT and cursor_pos < len(edit_text):
                cursor_pos += 1

    except Exception as e:
        logger = Logger.get_logger()
        logger.error(f"Error in excluded processes editor: {e}")
        return current_keywords
    finally:
        curses.curs_set(0)  # Hide cursor


def draw_panel_with_scrolling(
    stdscr: curses.window,
    title: str,
    data: dict,
    y: int,
    x: int,
    w: int,
    h: int,
    scroll_offset: int = 0,
    is_active: bool = False,
    selected_line: int = 0,
):
    """Draw a panel with scrolling support and active indicator."""
    logger = Logger.get_logger()

    try:
        panel_area = curses.newwin(h, w, y, x)
        panel_area.keypad(True)
        panel_area.nodelay(True)
        panel_area.scrollok(True)
        panel_area.timeout(1000)

        # Draw enhanced title bar with active indicator
        if is_active:
            title_text = f" * {title} * [ACTIVE] "
            title_color = ColorPair.BLACK_ON_YELLOW
        else:
            title_text = f" * {title} * "
            title_color = ColorPair.BRIGHT_WHITE_ON_BLUE

        padding = max(0, w - len(title_text))
        left_pad = padding // 2
        right_pad = padding - left_pad

        full_title = " " * left_pad + title_text + " " * right_pad
        panel_area.addstr(
            0, 0, full_title, curses.A_BOLD | curses.color_pair(title_color)
        )

        text_area_height = h
        text_area_width = w - 2
        row = 1

        for key, value in data.items():
            if row >= text_area_height:
                break

            if isinstance(value, list):
                # Handle tabular data with scrolling
                row = _draw_tabular_data_with_scrolling(
                    panel_area,
                    key,
                    value,
                    row,
                    text_area_width,
                    text_area_height,
                    scroll_offset,
                    selected_line,
                )
            else:
                # Handle simple key-value pairs
                row = _draw_simple_data(panel_area, key, value, row, text_area_width)

        panel_area.refresh()

    except Exception as e:
        logger.exception(f"Error drawing panel '{title}': {e}")


def _draw_tabular_data_with_scrolling(
    panel_area: curses.window,
    key: str,
    value: list,
    row: int,
    text_area_width: int,
    text_area_height: int,
    scroll_offset: int,
    selected_line: int = 0,
) -> int:
    """Draw tabular data with scrolling support."""
    try:
        panel_area.addstr(
            row, 0, f"{key}:", curses.color_pair(ColorPair.YELLOW_ON_BLACK)
        )
        row += 1

        if not value:
            return row

        # Calculate column widths
        col_widths = []
        for i in range(len(value[0])):
            col_widths.append(max(len(str(value[j][i])) for j in range(len(value))))

        # Distribute extra space
        if sum(col_widths) < text_area_width:
            diff = text_area_width - sum(col_widths)
            add_per_col = diff // len(col_widths) if col_widths else 0
            for i in range(len(col_widths)):
                col_widths[i] += add_per_col

        # Apply scrolling - skip header and apply offset
        visible_lines = text_area_height - row - 1
        start_index = 1 + scroll_offset  # Skip header (index 0) and apply scroll
        end_index = min(start_index + visible_lines, len(value))

        # Always show header first
        if len(value) > 0:
            header_line = value[0]
            formatted_header = []
            for i, cell in enumerate(header_line):
                if i < len(col_widths):
                    formatted_header.append(str(cell).ljust(col_widths[i]))
                else:
                    formatted_header.append(str(cell))

            header_str = " ".join(formatted_header)
            if len(header_str) > text_area_width:
                header_str = header_str[: text_area_width - 3] + "..."

            panel_area.addstr(
                row,
                0,
                header_str,
                curses.A_BOLD | curses.color_pair(ColorPair.CYAN_ON_BLACK),
            )
            row += 1

        # Draw scrolled data rows
        for line_index in range(start_index, end_index):
            if row >= text_area_height:
                break

            line = value[line_index]

            # Parse color information and create formatted string
            formatted_line = []
            base_color = ColorPair.WHITE_ON_BLACK

            for i, cell in enumerate(line):
                cell_text, cell_color = Theme.parse_color_prefix(str(cell))
                if cell_color != ColorPair.WHITE_ON_BLACK:
                    base_color = cell_color

                # Pad cell to column width
                if i < len(col_widths):
                    formatted_line.append(cell_text.ljust(col_widths[i]))
                else:
                    formatted_line.append(cell_text)

            str_to_print = " ".join(formatted_line)
            if len(str_to_print) > text_area_width:
                str_to_print = str_to_print[: text_area_width - 3] + "..."

            # Check if this is the selected line (adjust for header offset)
            data_line_index = (
                line_index - 1
            )  # Convert to 0-based data index (excluding header)
            is_selected = data_line_index == selected_line

            if is_selected:
                # Highlight selected line with magenta background
                display_color = ColorPair.BLACK_ON_MAGENTA
                attributes = curses.A_BOLD
            else:
                # Get alternating row color for subtle striping
                display_color, attributes = Theme.get_row_color(base_color, line_index)

            # Fill the entire row width with the background color for striping effect
            str_to_print = str_to_print.ljust(text_area_width)

            panel_area.addstr(
                row, 0, str_to_print, curses.color_pair(display_color) | attributes
            )
            row += 1

        # Show scroll indicators if needed
        if len(value) > visible_lines + 1:  # +1 for header
            try:
                indicator_col = text_area_width - 1
                # Up arrow if scrolled down
                if scroll_offset > 0:
                    panel_area.addstr(
                        2,
                        indicator_col,
                        "↑",
                        curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                    )
                # Down arrow if more items below
                if start_index + visible_lines < len(value):
                    panel_area.addstr(
                        text_area_height - 2,
                        indicator_col,
                        "↓",
                        curses.color_pair(ColorPair.YELLOW_ON_BLACK),
                    )
            except curses.error as e:
                logger = Logger.get_logger()
                logger.error(f"Failed to draw scroll indicators: {e}")

        return row

    except Exception as e:
        Logger.log_warning(f"Error drawing tabular data: {e}")
        return row


def draw_top_menu(stdscr: curses.window, mode: str) -> None:
    """Draw the top menu bar."""
    try:
        height, width = stdscr.getmaxyx()

        # Clear the top line
        stdscr.addstr(0, 0, " " * width, curses.color_pair(ColorPair.BLACK_ON_WHITE))

        # Sensors tab
        sensors_color = (
            ColorPair.BLACK_ON_YELLOW if mode == "system" else ColorPair.BLACK_ON_WHITE
        )
        stdscr.addstr(
            0, 0, " F2 Sensors ", curses.A_BOLD | curses.color_pair(sensors_color)
        )

        # Separator
        stdscr.addstr(0, 12, " | ", curses.color_pair(ColorPair.BLACK_ON_WHITE))

        # News tab
        news_color = (
            ColorPair.BLACK_ON_YELLOW if mode == "news" else ColorPair.BLACK_ON_WHITE
        )
        stdscr.addstr(0, 15, " F3 News ", curses.A_BOLD | curses.color_pair(news_color))

        # Separator
        stdscr.addstr(0, 24, " | ", curses.color_pair(ColorPair.BLACK_ON_WHITE))

        # Network tab
        network_color = (
            ColorPair.BLACK_ON_YELLOW if mode == "network" else ColorPair.BLACK_ON_WHITE
        )
        stdscr.addstr(
            0, 27, " F4 Network ", curses.A_BOLD | curses.color_pair(network_color)
        )

        # Help on the right
        help_text = " F1/? Help "
        help_x = width - len(help_text)
        stdscr.addstr(0, help_x, help_text, curses.color_pair(ColorPair.BLACK_ON_WHITE))

    except curses.error:
        pass


def _draw_simple_data(
    panel_area: curses.window, key: str, value: str, row: int, text_area_width: int
) -> int:
    """Draw simple key-value data within a panel."""
    try:
        # Parse color information
        clean_value, color = Theme.parse_color_prefix(str(value))

        str_to_print = f"{key}: {clean_value}"
        if len(str_to_print) > text_area_width:
            str_to_print = str_to_print[: text_area_width - 3] + "..."

        panel_area.addstr(row, 0, f"{key}:", curses.color_pair(ColorPair.CYAN_ON_BLACK))
        panel_area.addstr(row, len(key) + 2, clean_value, curses.color_pair(color))
        return row + 1

    except Exception as e:
        Logger.log_warning(f"Error drawing simple data: {e}")
        return row


def show_confirmation_modal(stdscr: curses.window, message: str) -> bool:
    """Show a confirmation modal dialog. Returns True if user confirms (Y), False otherwise."""
    height, width = stdscr.getmaxyx()
    
    modal_width = min(60, width - 4)
    modal_height = 7
    modal_y = (height - modal_height) // 2
    modal_x = (width - modal_width) // 2
    
    try:
        modal = curses.newwin(modal_height, modal_width, modal_y, modal_x)
        modal.keypad(True)
        modal.nodelay(False)
        
        modal.box()
        modal.addstr(0, 2, " Confirmation ", curses.A_BOLD | curses.color_pair(ColorPair.BLACK_ON_YELLOW))
        
        lines = message.split('\n')
        for i, line in enumerate(lines[:3]):
            if len(line) > modal_width - 4:
                line = line[:modal_width - 7] + "..."
            modal.addstr(2 + i, 2, line, curses.color_pair(ColorPair.WHITE_ON_BLACK))
        
        prompt = "Press Y to confirm, N to cancel"
        prompt_x = (modal_width - len(prompt)) // 2
        modal.addstr(modal_height - 2, prompt_x, prompt, curses.A_BOLD | curses.color_pair(ColorPair.YELLOW_ON_BLACK))
        
        modal.refresh()
        
        while True:
            key = modal.getch()
            if key in [ord('y'), ord('Y')]:
                return True
            elif key in [ord('n'), ord('N'), 27]:  # 27 is ESC
                return False
                
    except Exception as e:
        Logger.log_warning(f"Error showing confirmation modal: {e}")
        return False
