"""RSS/Atom feed reader for early signal detection.

Fetches recent items from RSS feeds to catch signals before Google indexes them.
"""

import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from src.state import SearchResult
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class RSSFeedReader:
    """Fetches and parses RSS/Atom feeds for early signal detection."""

    # Priority feeds for AI/ML research monitoring
    FEEDS = {
        # Official blogs - high signal, authoritative
        "openai_blog": {
            "url": "https://openai.com/blog/rss.xml",
            "description": "OpenAI official blog",
            "priority": "high"
        },
        "anthropic_blog": {
            "url": "https://www.anthropic.com/news/rss.xml",
            "description": "Anthropic news and research",
            "priority": "high"
        },
        "google_ai_blog": {
            "url": "https://blog.google/technology/ai/rss/",
            "description": "Google AI blog",
            "priority": "high"
        },
        "meta_ai_blog": {
            "url": "https://ai.meta.com/blog/rss/",
            "description": "Meta AI research blog",
            "priority": "high"
        },

        # Research papers - academic sources
        "arxiv_cs_ai": {
            "url": "http://export.arxiv.org/rss/cs.AI",
            "description": "arXiv CS.AI (Artificial Intelligence)",
            "priority": "medium"
        },
        "arxiv_cs_lg": {
            "url": "http://export.arxiv.org/rss/cs.LG",
            "description": "arXiv CS.LG (Machine Learning)",
            "priority": "medium"
        },
        "arxiv_cs_cl": {
            "url": "http://export.arxiv.org/rss/cs.CL",
            "description": "arXiv CS.CL (Computation and Language)",
            "priority": "medium"
        },

        # Community hubs - trending discussions
        "huggingface_blog": {
            "url": "https://huggingface.co/blog/feed.xml",
            "description": "Hugging Face blog",
            "priority": "high"
        },
        "papers_with_code": {
            "url": "https://paperswithcode.com/latest/rss",
            "description": "Papers with Code latest",
            "priority": "medium"
        },

        # Industry news - business intelligence
        "mit_tech_ai": {
            "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
            "description": "MIT Technology Review AI",
            "priority": "medium"
        },
        "venturebeat_ai": {
            "url": "https://venturebeat.com/category/ai/feed/",
            "description": "VentureBeat AI news",
            "priority": "low"
        },

        # Research institutions
        "deepmind_blog": {
            "url": "https://deepmind.google/blog/rss.xml",
            "description": "Google DeepMind blog",
            "priority": "high"
        },
    }

    def __init__(self, timeout: int = 10):
        """Initialize RSS feed reader.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout

    async def fetch_feed(self, feed_url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse a single RSS/Atom feed.

        Args:
            feed_url: URL of the RSS/Atom feed

        Returns:
            Parsed feed dict or None if fetch failed
        """
        try:
            # Use aiohttp for async fetching
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url, timeout=self.timeout) as response:
                    if response.status == 200:
                        content = await response.text()
                        # Parse with feedparser
                        feed = feedparser.parse(content)

                        if feed.bozo:  # Feed has errors
                            logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")

                        return feed
                    else:
                        logger.warning(f"Feed fetch failed: {feed_url} (HTTP {response.status})")
                        return None

        except asyncio.TimeoutError:
            logger.warning(f"Feed fetch timeout: {feed_url}")
            return None
        except Exception as e:
            logger.warning(f"Feed fetch error for {feed_url}: {e}")
            return None

    def _parse_date(self, entry) -> Optional[datetime]:
        """Parse publication date from feed entry.

        Args:
            entry: Feed entry dict

        Returns:
            datetime object or None if parsing failed
        """
        # Try different date fields
        for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
            if hasattr(entry, date_field):
                time_struct = getattr(entry, date_field)
                if time_struct:
                    try:
                        return datetime(*time_struct[:6])
                    except Exception:
                        pass

        return None

    def _entry_to_search_result(
        self,
        entry,
        feed_name: str,
        feed_description: str
    ) -> SearchResult:
        """Convert RSS entry to SearchResult format.

        Args:
            entry: Feed entry dict
            feed_name: Name of the feed
            feed_description: Description of the feed

        Returns:
            SearchResult object
        """
        # Extract fields with fallbacks
        title = entry.get('title', 'Untitled')
        url = entry.get('link', '')

        # Get summary/content
        snippet = ""
        if hasattr(entry, 'summary'):
            snippet = entry.summary[:500]  # Limit snippet length
        elif hasattr(entry, 'description'):
            snippet = entry.description[:500]

        # Get full content if available
        content = None
        if hasattr(entry, 'content') and entry.content:
            # content is usually a list of dicts
            if isinstance(entry.content, list) and len(entry.content) > 0:
                content = entry.content[0].get('value', '')[:5000]  # Limit content length
        elif hasattr(entry, 'summary_detail'):
            content = entry.summary_detail.get('value', '')[:5000]

        # Add source metadata to snippet
        pub_date = self._parse_date(entry)
        date_str = pub_date.strftime("%Y-%m-%d") if pub_date else "Unknown date"
        snippet = f"[RSS: {feed_description}] [{date_str}] {snippet}"

        return SearchResult(
            query=f"RSS: {feed_name}",
            title=title,
            url=url,
            snippet=snippet,
            content=content
        )

    async def fetch_recent(
        self,
        days: int = 7,
        feed_names: Optional[List[str]] = None,
        priority_filter: Optional[str] = None,
        max_items_per_feed: int = 10
    ) -> List[SearchResult]:
        """Fetch recent items from RSS feeds.

        Args:
            days: Number of days back to fetch items
            feed_names: Specific feed names to fetch (None = all feeds)
            priority_filter: Filter by priority ("high", "medium", "low", None = all)
            max_items_per_feed: Maximum items to return per feed

        Returns:
            List of SearchResult objects
        """
        logger.info(f"Fetching RSS feeds (last {days} days, priority={priority_filter or 'all'})")

        cutoff_date = datetime.now() - timedelta(days=days)
        results = []

        # Filter feeds based on criteria
        feeds_to_fetch = {}
        for feed_name, feed_config in self.FEEDS.items():
            # Filter by specific feed names
            if feed_names and feed_name not in feed_names:
                continue

            # Filter by priority
            if priority_filter and feed_config["priority"] != priority_filter:
                continue

            feeds_to_fetch[feed_name] = feed_config

        logger.info(f"Fetching {len(feeds_to_fetch)} feeds")

        # Fetch feeds concurrently
        fetch_tasks = [
            self.fetch_feed(config["url"])
            for config in feeds_to_fetch.values()
        ]

        feed_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Process each feed
        for (feed_name, feed_config), feed_data in zip(feeds_to_fetch.items(), feed_results):
            # Skip failed fetches
            if isinstance(feed_data, Exception) or feed_data is None:
                logger.warning(f"Skipping {feed_name} due to fetch failure")
                continue

            # Process entries
            items_added = 0
            for entry in feed_data.entries:
                # Check date
                pub_date = self._parse_date(entry)
                if pub_date and pub_date < cutoff_date:
                    continue  # Too old

                # Convert to SearchResult
                result = self._entry_to_search_result(
                    entry,
                    feed_name,
                    feed_config["description"]
                )

                results.append(result)
                items_added += 1

                if items_added >= max_items_per_feed:
                    break

            logger.info(f"Added {items_added} items from {feed_name}")

        logger.info(f"Total RSS items fetched: {len(results)}")
        return results

    async def fetch_by_topic(
        self,
        topic: str,
        days: int = 7,
        max_items: int = 20
    ) -> List[SearchResult]:
        """Fetch RSS items relevant to a specific topic.

        Uses keyword matching to filter items by relevance.

        Args:
            topic: Research topic
            days: Number of days back to fetch
            max_items: Maximum total items to return

        Returns:
            List of relevant SearchResult objects
        """
        logger.info(f"Fetching RSS feeds for topic: {topic}")

        # Fetch all recent items
        all_items = await self.fetch_recent(
            days=days,
            priority_filter="high"  # Focus on high-priority feeds for topic matching
        )

        # Extract keywords from topic (simple approach)
        topic_lower = topic.lower()
        keywords = set(topic_lower.split())

        # Filter by relevance (simple keyword matching)
        relevant_items = []
        for item in all_items:
            # Check if any keyword appears in title or snippet
            title_lower = item.title.lower()
            snippet_lower = item.snippet.lower()

            if any(keyword in title_lower or keyword in snippet_lower for keyword in keywords):
                relevant_items.append(item)

        logger.info(f"Found {len(relevant_items)} relevant items for topic: {topic}")

        # Return top N most recent
        return relevant_items[:max_items]

    @classmethod
    def get_available_feeds(cls) -> Dict[str, Dict[str, str]]:
        """Get list of available RSS feeds.

        Returns:
            Dictionary of feed configurations
        """
        return cls.FEEDS.copy()

    @classmethod
    def get_feeds_by_priority(cls, priority: str) -> List[str]:
        """Get feed names filtered by priority.

        Args:
            priority: Priority level ("high", "medium", "low")

        Returns:
            List of feed names
        """
        return [
            name for name, config in cls.FEEDS.items()
            if config["priority"] == priority
        ]
