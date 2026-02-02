"""Article content fetcher and markdown converter."""

import html2text
from newspaper import Article

from ..core.logger import Logger


class ArticleFetcher:
    """Fetch full article content and convert to markdown."""

    def __init__(self):
        """Initialize article fetcher."""
        self.logger = Logger.get_logger()
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # Don't wrap text

    def fetch_article(self, url: str) -> str:
        """Fetch article from URL and convert to markdown."""
        try:
            self.logger.debug(f"Fetching article from: {url}")

            article = Article(url)
            article.download()
            article.parse()

            # Build markdown content
            markdown_parts = []

            if article.title:
                markdown_parts.append(f"# {article.title}\n")

            if article.authors:
                markdown_parts.append(f"**Authors:** {', '.join(article.authors)}\n")

            if article.publish_date:
                markdown_parts.append(f"**Published:** {article.publish_date}\n")

            markdown_parts.append("---\n")

            if article.text:
                # Use the parsed text which is already clean
                markdown_parts.append(article.text)
            else:
                # Fallback to converting HTML
                self.logger.debug("No parsed text, converting HTML")
                markdown_parts.append(self.html_converter.handle(article.html))

            result = "\n".join(markdown_parts)
            self.logger.info(f"Successfully fetched article ({len(result)} chars)")
            return result

        except Exception as e:
            error_msg = f"Failed to fetch article: {str(e)}"
            self.logger.error(error_msg)
            return f"# Error\n\n{error_msg}\n\nURL: {url}"
