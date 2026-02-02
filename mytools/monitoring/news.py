import curses
import os

import feedparser  # type: ignore
import requests
from bs4 import BeautifulSoup

from .article_fetcher import ArticleFetcher

sources = [
    "https://hackaday.com/blog/feed/",
    "https://www.engadget.com/rss.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://techcrunch.com/feed/",
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://lobste.rs/rss",
]

ACCEPT_HEADER: str = (
    "application/atom+xml"
    ",application/rdf+xml"
    ",application/rss+xml"
    ",application/x-netcdf"
    ",application/xml"
    ";q=0.9,text/xml"
    ";q=0.2,*/*"
    ";q=0.1"
)

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": ACCEPT_HEADER,
}


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
    content = requests.get(sources[index].strip(), headers=headers)
    if content.status_code >= 400:
        return [
            f"{content.status_code}: Unable to get news from {sources[index]}",
            f"{content.content}",
        ]
    feed = feedparser.parse(content.content)
    news = []
    for entry in feed.entries:
        title = f"[{entry.published_parsed.tm_mday}.{entry.published_parsed.tm_mon}.{entry.published_parsed.tm_year} {entry.published_parsed.tm_hour}:{entry.published_parsed.tm_min}] {entry.title}"
        news.append(title)
        try:
            soup = BeautifulSoup(entry.summary, "lxml")
            texts = soup.findAll(text=True)
        except Exception:
            texts = [title, entry.get("title_detail", {}).get("value")]

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
            link = news_cache[news[news_index]]["link"]

            # Show loading message
            loading_win = curses.newwin(5, 50, height // 2 - 2, width // 2 - 25)
            loading_win.box()
            loading_win.addstr(
                2, 2, "Fetching article content...", curses.color_pair(1)
            )
            loading_win.refresh()

            # Fetch full article
            article_fetcher = ArticleFetcher()
            article_content = article_fetcher.fetch_article(link)

            # Clear loading message
            loading_win.clear()
            loading_win.refresh()
            del loading_win

            # Display article in scrollable window
            display_article_window(
                stdscr, article_content, news[news_index], width, height
            )

        except Exception as e:
            news_area.addstr(1, 2, f"Error: {e}")
            news_area.refresh()
            return


def display_article_window(
    stdscr: curses.window, content: str, title: str, width: int, height: int
):
    """Display article content in a scrollable window."""
    new_win_height = height - 4
    new_win_width = width - 4

    news_window = curses.newwin(new_win_height, new_win_width, 2, 2)
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
            wrapped = wrap_text(line, text_width)
            content_lines.extend(wrapped)

    scroll_pos = 0
    max_scroll = max(0, len(content_lines) - text_height)

    while True:
        news_window.clear()
        news_window.box()

        # Display title
        truncated_title = (
            title[: new_win_width - 4] if len(title) > new_win_width - 4 else title
        )
        news_window.addstr(0, 2, truncated_title, curses.color_pair(2))

        # Display help text at bottom
        help_text = "[PgUp/PgDn: Scroll] [q/ESC: Close]"
        news_window.addstr(new_win_height - 1, 2, help_text, curses.color_pair(1))

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
                curses.color_pair(2),
            )

        news_window.refresh()

        # Handle input
        key = news_window.getch()

        if key == ord("q") or key == 27:  # q or ESC
            break
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
