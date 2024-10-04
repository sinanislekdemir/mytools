import curses
import os

import feedparser  # type: ignore
import lxml
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
        soup = BeautifulSoup(entry.summary, "lxml")
        texts = soup.findAll(text=True)

        summary_text = "".join(texts)
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

    height, width = stdscr.getmaxyx()
    news_area_height = height
    news_area_width = width
    news_area_x = 0
    news_area_y = 1

    news_area = curses.newwin(
        news_area_height, news_area_width, news_area_y, news_area_x
    )

    def print_loading():
        news_area.addstr(1, 0, "Loading news...", curses.color_pair(1))
        news_area.refresh()

    def print_border():
        title = sources[source_index]
        news_area.clear()
        news_area.addstr(
            news_area_height - 2,
            0,
            title,
            curses.A_BOLD,
        )

    print_border()

    if news is None:
        print_loading()
        news = get_news(source_index)

    if key == 9:
        source_index = (source_index + 1) % len(sources)
        print_border()
        print_loading()
        news = get_news(source_index)
        news_index = 0

    if key == ord("r"):
        print_loading()
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
        print_border()
        print_loading()
        news = get_news(source_index)
        news_index = 0

    if key == curses.KEY_RIGHT:
        source_index = (source_index + 1) % len(sources)
        print_border()
        print_loading()
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
            news_area.addstr(i, 0, line.ljust(news_area_width), curses.color_pair(5))
        else:
            news_area.addstr(i, 0, line)
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
            new_win_height = height - 20
            new_win_width = width - 20

            news_window = curses.newwin(new_win_height, new_win_width, 10, 10)
            news_window.clear()
            news_window.box()

            text_box = news_window.subwin(new_win_height - 4, new_win_width - 4, 12, 12)
            text_box.clear()

            news_window.addstr(0, 2, news[news_index], curses.color_pair(2))
            for i, line in enumerate(wrap_text(news_text, news_width - 8)):
                text_box.addstr(i, 1, line)
                if i == height - 22:
                    break

            text_box.refresh()
            news_window.refresh()
        except Exception as e:
            news_area.addstr(1, 2, f"Error: {e}")
            news_area.refresh()
            return
