"""News caching functionality."""

from typing import Dict, Optional

from ..core.logger import Logger


class NewsCache:
    """Cache for news items with links and summaries."""

    def __init__(self):
        """Initialize news cache."""
        self.logger = Logger.get_logger()
        self.cache: Dict[str, Dict[str, str]] = {}

    def store_item(self, title: str, link: str, summary: str) -> None:
        """Store a news item in the cache."""
        try:
            self.cache[title] = {"link": link, "summary": summary}
            self.logger.debug(f"Cached news item: {title[:50]}...")

        except Exception as e:
            self.logger.warning(f"Error storing cache item: {e}")

    def get_link(self, title: str) -> Optional[str]:
        """Get link for a news item."""
        try:
            item = self.cache.get(title)
            return item["link"] if item else None

        except Exception as e:
            self.logger.warning(f"Error getting link from cache: {e}")
            return None

    def get_summary(self, title: str) -> Optional[str]:
        """Get summary for a news item."""
        try:
            item = self.cache.get(title)
            return item["summary"] if item else None

        except Exception as e:
            self.logger.warning(f"Error getting summary from cache: {e}")
            return None

    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.logger.debug("News cache cleared")

    def get_cache_size(self) -> int:
        """Get number of items in cache."""
        return len(self.cache)
