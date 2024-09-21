import curses
import time

from mytools.netwatch import clean_past_data, network_loop, toggle_hide_http
from mytools.news import news_loop
from mytools.sensors import switch_combined, switch_hide_command, system_loop


def main_loop(stdscr: curses.window):
    stdscr.clear()
    stdscr.refresh()
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.cbreak()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(9, curses.COLOR_CYAN, curses.COLOR_BLACK)

    last_size = (0, 0)

    mode = "system"

    while True:
        # get screen size
        height, width = stdscr.getmaxyx()
        if (height, width) != last_size:
            stdscr.clear()
            last_size = (height, width)

        key = stdscr.getch()
        if key == ord("q"):
            break
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

        sensors_color = 1
        if mode == "system":
            sensors_color = 6
        stdscr.addstr(0, 0, " [F2] Sensors ", curses.color_pair(sensors_color))
        news_color = 1
        if mode == "news":
            news_color = 6
        stdscr.addstr(0, 14, " [F3] News ", curses.color_pair(news_color))
        network_color = 1
        if mode == "network":
            network_color = 6
        stdscr.addstr(0, 26, " [F4] Network ", curses.color_pair(network_color))

        if mode == "system":
            if key == ord("h"):
                switch_hide_command()
            if key == ord("c"):
                switch_combined()
            system_loop(stdscr)
            stdscr.refresh()
            time.sleep(1)

        if mode == "network":
            if key == ord("c"):
                clean_past_data()
            if key == ord("h"):
                toggle_hide_http()
                network_loop(stdscr)
            network_loop(stdscr)
            stdscr.refresh()
            time.sleep(1)

        elif mode == "news":
            news_loop(stdscr, key)
            stdscr.refresh()


def main():
    curses.wrapper(main_loop)

if __name__ == "__main__":
    main()
