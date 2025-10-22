"""News fetching functionality."""

from typing import List

import feedparser  # type: ignore
import requests
from bs4 import BeautifulSoup

from ..core.config import Config
from ..core.logger import Logger
from .news_cache import NewsCache


class NewsFetcher:
    """Handle news fetching from RSS feeds."""

    def __init__(self, news_cache: NewsCache):
        """Initialize news fetcher with cache."""
        self.logger = Logger.get_logger()
        self.headers = Config.HTTP_HEADERS
        self.cache = news_cache

    def fetch_news(self, source_url: str) -> List[str]:
        """Fetch news from a single RSS source."""
        try:
            self.logger.debug(f"Fetching news from: {source_url}")

            response = requests.get(
                source_url.strip(), headers=self.headers, timeout=10
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                self.logger.warning(f"No entries found in feed: {source_url}")
                return [f"No news available from {source_url}"]

            news_items = []
            for entry in feed.entries:
                # Format the title with publication date
                try:
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_date = entry.published_parsed
                        date_str = f"[{pub_date.tm_mday}.{pub_date.tm_mon}.{pub_date.tm_year} {pub_date.tm_hour}:{pub_date.tm_min:02d}]"
                    else:
                        date_str = "[No date]"

                    title = f"{date_str} {entry.title}"
                    news_items.append(title)

                    # Cache the item
                    link = getattr(entry, "link", "")
                    summary = self.extract_summary(entry)
                    self.cache.store_item(title, link, summary)

                except Exception as e:
                    self.logger.warning(f"Error parsing entry: {e}")
                    news_items.append(
                        f"[Parse Error] {getattr(entry, 'title', 'Unknown title')}"
                    )

            self.logger.info(f"Fetched {len(news_items)} news items from {source_url}")
            return news_items

        except requests.RequestException as e:
            error_msg = f"Network error fetching {source_url}: {e}"
            self.logger.error(error_msg)
            return [error_msg]

        except Exception as e:
            error_msg = f"Error parsing feed {source_url}: {e}"
            self.logger.exception(error_msg)
            return [error_msg]

    def extract_summary(self, entry) -> str:
        """Extract and clean summary text from feed entry."""
        try:
            if hasattr(entry, "summary"):
                soup = BeautifulSoup(entry.summary, "lxml")
                texts = soup.find_all(text=True)
                return "".join(texts)
            elif hasattr(entry, "title"):
                return entry.title
            else:
                return "No summary available"

        except Exception as e:
            self.logger.warning(f"Error extracting summary: {e}")
            return getattr(entry, "title", "Content unavailable")
