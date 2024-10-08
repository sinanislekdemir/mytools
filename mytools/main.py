import curses
import time
from threading import Thread

from mytools.netwatch import (clean_past_data, dump_past_data,
                              get_ss_tnp_output, network_loop,
                              toggle_hide_http)
from mytools.news import news_loop
from mytools.sensors import switch_combined, switch_hide_command, system_loop

running = False


def main_loop(stdscr: curses.window):
    global running

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
    curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_WHITE)

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
            running = False
            break

        if key == curses.KEY_F1 or key == ord("?"):
            helpwin = curses.newwin(17, 50, 5, 5)
            helpwin.box()
            helpwin.addstr(1, 2, "Help", curses.color_pair(1))
            helpwin.addstr(3, 2, "F1: Help", curses.color_pair(1))
            helpwin.addstr(4, 2, "F2: Sensors", curses.color_pair(1))
            helpwin.addstr(5, 2, "F3: News", curses.color_pair(1))
            helpwin.addstr(6, 2, "F4: Network", curses.color_pair(1))
            helpwin.addstr(7, 2, "Q: Quit", curses.color_pair(1))

            helpwin.addstr(1, 14, "Sensor View:", curses.color_pair(2))
            helpwin.addstr(2, 14, "C: Combined view", curses.color_pair(1))
            helpwin.addstr(3, 14, "H: Hide command", curses.color_pair(1))

            helpwin.addstr(4, 14, "News View:", curses.color_pair(2))
            helpwin.addstr(5, 14, "Left/Right: Change source", curses.color_pair(1))
            helpwin.addstr(6, 14, "Enter: Read news", curses.color_pair(1))
            helpwin.addstr(7, 14, "O: Browse news", curses.color_pair(1))

            helpwin.addstr(8, 14, "Network View:", curses.color_pair(2))
            helpwin.addstr(9, 14, "C: Clean past data", curses.color_pair(1))
            helpwin.addstr(10, 14, "H: Hide HTTP", curses.color_pair(1))
            helpwin.addstr(11, 14, "R: Refresh", curses.color_pair(1))
            helpwin.addstr(12, 14, "D: Dump past data", curses.color_pair(1))
            helpwin.addstr(
                13, 2, "You can edit ~/.news_sources.txt", curses.color_pair(1)
            )
            helpwin.addstr(14, 2, "to add your own news sources", curses.color_pair(1))

            helpwin.addnstr(15, 14, "sinan@islekdemir.com", 20, curses.color_pair(3))
            helpwin.refresh()
            key = helpwin.getch()

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

        sensors_color = 10

        stdscr.addstr(0, 0, (" " * width), curses.color_pair(10))
        if mode == "system":
            sensors_color = 6

        stdscr.addstr(
            0, 0, "[F2] Sensors ", curses.A_BOLD | curses.color_pair(sensors_color)
        )
        stdscr.addstr(0, 13, "|", curses.color_pair(10))
        news_color = 10
        if mode == "news":
            news_color = 6

        stdscr.addstr(
            0, 14, " [F3] News  ", curses.A_BOLD | curses.color_pair(news_color)
        )
        stdscr.addstr(0, 26, "|", curses.color_pair(10))
        network_color = 10
        if mode == "network":
            network_color = 6

        stdscr.addstr(
            0, 28, " [F4] Network ", curses.A_BOLD | curses.color_pair(network_color)
        )
        stdscr.addstr(0, 42, "|", curses.color_pair(10))

        stdscr.addstr(0, width - 14, " [F1/?] Help ", curses.color_pair(10))

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
            if key == ord("d"):
                dump_past_data()
            network_loop(stdscr)
            stdscr.refresh()
            time.sleep(1)

        elif mode == "news":
            news_loop(stdscr, key)
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
