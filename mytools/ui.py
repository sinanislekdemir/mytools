import curses

CORNER_LEFT_UP = "┌"
CORNER_RIGHT_UP = "┐"
CORNER_LEFT_DOWN = "└"
CORNER_RIGHT_DOWN = "┘"
HORIZONTAL_LINE = "─"
VERTICAL_LINE = "│"


def draw_panel(
    stdscr: curses.window, title: str, data: dict, y: int, x: int, w: int, h: int
):
    """Draw a panel with a title and data in a box"""
    panel_area = curses.newwin(h, w, y, x)
    panel_area.box()
    panel_area.keypad(True)
    panel_area.nodelay(True)
    panel_area.scrollok(True)
    panel_area.timeout(1000)
    panel_area.addstr(0, 2, f"[{title}]", curses.color_pair(8))

    text_area_height = h - 2
    text_area_width = w - 2
    # Fit data to text area
    row = 1
    for key, value in data.items():
        if row >= text_area_height:
            break
        if isinstance(value, list):
            panel_area.addstr(row, 1, f"{key}:", curses.color_pair(2))

            row += 1

            # print tabular data
            # first row is the header
            # the rest are the values
            col_widths = []

            for i in range(len(value[0])):
                col_widths.append(max(len(value[j][i]) for j in range(len(value))))

            if sum(col_widths) < text_area_width:
                diff = text_area_width - sum(col_widths)
                add_per_col = diff // len(col_widths)
                for i in range(len(col_widths)):
                    col_widths[i] += add_per_col

            for line in value:
                if row >= text_area_height:
                    break
                color = 1
                for i in range(len(line)):
                    if line[i].startswith("GREEN!"):
                        color = 3
                        line[i] = line[i][6:]
                    if line[i].startswith("RED!"):
                        color = 7
                        line[i] = line[i][4:]
                    if line[i].startswith("YELLOW!"):
                        color = 6
                        line[i] = line[i][7:]
                str_to_print = f"{' '.join([line[i].ljust(col_widths[i]) for i in range(len(line))])}"

                if len(str_to_print) > text_area_width:
                    str_to_print = str_to_print[: text_area_width - 3] + "..."

                panel_area.addstr(row, 1, str_to_print, curses.color_pair(color))
                row += 1
            continue

        color = 1
        if str(value).startswith("RED!"):
            value = value[4:]
            color = 7
        if str(value).startswith("YELLOW!"):
            value = value[7:]
            color = 6

        str_to_print = f"{key}: {value}"
        if len(str_to_print) > text_area_width:
            str_to_print = str_to_print[: text_area_width - 3] + "..."

        panel_area.addstr(row, 1, key + ":", curses.color_pair(9))
        panel_area.addstr(
            row, len(key) + 3, str_to_print[len(key) + 2 :], curses.color_pair(color)
        )
        row += 1
    panel_area.refresh()
