import curses
import os

import feedparser  # type: ignore
from bs4 import BeautifulSoup

sources = [
    "https://hackaday.com/blog/feed/",
    "https://www.engadget.com/rss.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://techcrunch.com/feed/",
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://lobste.rs/rss",
]


def load_sources():
    global sources
    sources_file = "news_sources.txt"
    home_sources_file = os.path.expanduser("~/.news_sources.txt")

    if os.path.exists(sources_file):
        with open(sources_file, "r") as f:
            sources = f.readlines()
    elif os.path.exists(home_sources_file):
        with open(home_sources_file, "r") as f:
            sources = f.readlines()
    else:
        print("No sources file found. Using default sources.")


news_cache = {}
source_index = 0
news_index = 0
news = None


def get_news(index: int) -> list:
    global news_cache
    feed = feedparser.parse(sources[index])
    news = []
    for entry in feed.entries:
        title = f"[{entry.published_parsed.tm_mday}.{entry.published_parsed.tm_mon}.{entry.published_parsed.tm_year} {entry.published_parsed.tm_hour}:{entry.published_parsed.tm_min}] {entry.title}"
        news.append(title)
        soup = BeautifulSoup(entry.summary, "html.parser")
        summary_text = soup.get_text()
        news_cache[title] = {
            "link": entry.link,
            "summary": summary_text,
        }
    return news


def wrap_text(text: str, width: int) -> list[str]:
    lines = []
    words = text.split(" ")
    current_line = ""

    for word in words:
        # Check if adding the next word exceeds the width
        if len(current_line) + len(word) + 1 <= width:
            current_line += word + " "
        else:
            lines.append(current_line.strip())
            current_line = word + " "

    if current_line:
        lines.append(current_line.strip())

    return lines


def news_loop(stdscr: curses.window, key: int):
    global source_index
    global news_index
    global news
    load_sources()

    def print_loading(win: curses.window):
        win.clear()
        print_border(win)
        win.addstr(1, 2, "Loading news...", curses.color_pair(1))
        win.refresh()

    def print_border(win: curses.window):
        win.box()
        win.refresh()
        win.keypad(True)
        win.nodelay(True)
        win.scrollok(True)
        win.timeout(1000)
        win.addstr(0, 2, "[", curses.color_pair(0))
        win.addstr(0, 3, f"News {sources[source_index]}", curses.color_pair(6))
        win.addstr(0, len(sources[source_index]) + 8, "]", curses.color_pair(0))
        win.refresh()

    height, width = stdscr.getmaxyx()
    news_area_height = height - 1
    news_area_width = width
    news_area_x = 0
    news_area_y = 1
    news_area = curses.newwin(
        news_area_height, news_area_width, news_area_y, news_area_x
    )
    print_border(news_area)

    if news is None:
        print_loading(news_area)
        news = get_news(source_index)

    if key == 9:
        source_index = (source_index + 1) % len(sources)
        print_border(news_area)
        print_loading(news_area)
        news = get_news(source_index)
        news_index = 0

    if key == ord("r"):
        print_loading(news_area)
        news = get_news(source_index)
        news_index = 0

    if key == curses.KEY_DOWN:
        news_index += 1
        if news_index >= len(news):
            news_index = 0

    elif key == curses.KEY_UP:
        news_index -= 1
        if news_index < 0:
            news_index = 0

    if key == curses.KEY_LEFT:
        source_index = (source_index - 1) % len(sources)
        print_border(news_area)
        print_loading(news_area)
        news = get_news(source_index)
        news_index = 0

    if key == curses.KEY_RIGHT:
        source_index = (source_index + 1) % len(sources)
        print_border(news_area)
        print_loading(news_area)
        news = get_news(source_index)
        news_index = 0

    elif key == curses.KEY_NPAGE:
        news_index += news_area_height - 2
        if news_index >= len(news):
            news_index = 0

    elif key == curses.KEY_PPAGE:
        news_index -= news_area_height - 2
        if news_index < 0:
            news_index = 0

    for i, line in enumerate(news):
        line = wrap_text(line, news_area_width - 3)[0]
        if i == news_index:
            news_area.addstr(
                i + 1, 2, line.ljust(news_area_width - 3), curses.color_pair(5)
            )
        else:
            news_area.addstr(i + 1, 2, line)
        if i == news_area_height - 3:
            break

    news_area.refresh()
    if key == ord("o") or key == ord("O"):
        # open the link in the browser
        link = news_cache[news[news_index]]["link"]
        # Open the link in the browser using xdg-open
        os.system(f"xdg-open {link} > /dev/null 2>&1 &")

    if key == curses.KEY_ENTER or key == 10:
        try:
            news_text = news_cache[news[news_index]]["summary"]
            news_width = width - 22
            news_window = curses.newwin(height - 20, width - 20, 10, 10)
            news_window.clear()
            news_window.box()

            news_window.addstr(0, 2, news[news_index], curses.color_pair(2))
            for i, line in enumerate(wrap_text(news_text, news_width)):
                news_window.addstr(2 + i, 2, line)
                if i == height - 22:
                    break
            news_window.refresh()
        except Exception as e:
            news_area.addstr(1, 2, f"Error: {e}")
            news_area.refresh()
            return
