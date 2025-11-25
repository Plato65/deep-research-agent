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
        # Official blogs - high signal, authoritative (low volume)
        "openai_blog": {
            "url": "https://openai.com/blog/rss.xml",
            "description": "OpenAI official blog",
            "priority": "high",
            "max_items": 10,  # Low volume, fetch all recent
            "require_keyword_match": False  # Trust all items from official blog
        },
        "anthropic_blog": {
            "url": "https://www.anthropic.com/news/rss.xml",
            "description": "Anthropic news and research",
            "priority": "high",
            "max_items": 10,
            "require_keyword_match": False
        },
        "google_ai_blog": {
            "url": "https://blog.google/technology/ai/rss/",
            "description": "Google AI blog",
            "priority": "high",
            "max_items": 10,
            "require_keyword_match": False
        },
        "meta_ai_blog": {
            "url": "https://ai.meta.com/blog/rss/",
            "description": "Meta AI research blog",
            "priority": "high",
            "max_items": 10,
            "require_keyword_match": False
        },

        # Research papers - HIGH VOLUME (150+ per day)
        "arxiv_cs_ai": {
            "url": "http://export.arxiv.org/rss/cs.AI",
            "description": "arXiv CS.AI (Artificial Intelligence)",
            "priority": "medium",
            "max_items": 200,  # Fetch more, filter by relevance
            "require_keyword_match": True,  # MUST match topic
            "return_top_n": 5  # Return only top 5 after filtering
        },
        "arxiv_cs_lg": {
            "url": "http://export.arxiv.org/rss/cs.LG",
            "description": "arXiv CS.LG (Machine Learning)",
            "priority": "medium",
            "max_items": 200,
            "require_keyword_match": True,
            "return_top_n": 5
        },
        "arxiv_cs_cl": {
            "url": "http://export.arxiv.org/rss/cs.CL",
            "description": "arXiv CS.CL (Computation and Language)",
            "priority": "medium",
            "max_items": 200,
            "require_keyword_match": True,
            "return_top_n": 5
        },

        # Community hubs - trending discussions
        "huggingface_blog": {
            "url": "https://huggingface.co/blog/feed.xml",
            "description": "Hugging Face blog",
            "priority": "high",
            "max_items": 15,
            "require_keyword_match": False
        },
        "papers_with_code": {
            "url": "https://paperswithcode.com/latest/rss",
            "description": "Papers with Code latest",
            "priority": "medium",
            "max_items": 20,
            "require_keyword_match": True,
            "return_top_n": 5
        },

        # Industry news - business intelligence
        "mit_tech_ai": {
            "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
            "description": "MIT Technology Review AI",
            "priority": "medium",
            "max_items": 15,
            "require_keyword_match": False
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

    def __init__(
        self,
        timeout: int = 10,
        enabled_feeds: Optional[List[str]] = None,
        disabled_feeds: Optional[List[str]] = None,
        custom_feeds: Optional[Dict[str, Dict]] = None
    ):
        """Initialize RSS feed reader.

        Args:
            timeout: HTTP request timeout in seconds
            enabled_feeds: List of specific feeds to enable (None = all)
            disabled_feeds: List of feeds to disable
            custom_feeds: Dictionary of custom feeds to add
        """
        self.timeout = timeout
        self.enabled_feeds = enabled_feeds
        self.disabled_feeds = disabled_feeds or []

        # Merge custom feeds into FEEDS
        self.feeds = self.FEEDS.copy()
        if custom_feeds:
            logger.info(f"Adding {len(custom_feeds)} custom RSS feeds")
            self.feeds.update(custom_feeds)

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

    def _matches_keywords(self, text: str, keywords: set) -> bool:
        """Check if text contains any of the keywords.

        Args:
            text: Text to search
            keywords: Set of keywords to match

        Returns:
            True if any keyword is found
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)

    def _calculate_relevance_score(self, item: SearchResult, keywords: set) -> float:
        """Calculate relevance score for an item based on keyword matches.

        Args:
            item: SearchResult to score
            keywords: Set of keywords to match

        Returns:
            Relevance score (higher is better)
        """
        score = 0.0
        title_lower = item.title.lower()
        snippet_lower = item.snippet.lower()

        # Title matches are worth more
        for keyword in keywords:
            if keyword in title_lower:
                score += 2.0
            if keyword in snippet_lower:
                score += 1.0

        return score

    async def fetch_recent(
        self,
        days: int = 7,
        feed_names: Optional[List[str]] = None,
        priority_filter: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[SearchResult]:
        """Fetch recent items from RSS feeds with smart filtering.

        Args:
            days: Number of days back to fetch items
            feed_names: Specific feed names to fetch (None = all feeds)
            priority_filter: Filter by priority ("high", "medium", "low", None = all)
            topic: Research topic for keyword filtering (None = no filtering)

        Returns:
            List of SearchResult objects
        """
        logger.info(f"Fetching RSS feeds (last {days} days, priority={priority_filter or 'all'}, topic={topic or 'none'})")

        cutoff_date = datetime.now() - timedelta(days=days)
        results = []

        # Extract keywords from topic if provided
        keywords = set()
        if topic:
            keywords = set(topic.lower().split())

        # Filter feeds based on criteria
        feeds_to_fetch = {}
        for feed_name, feed_config in self.feeds.items():
            # Skip if explicitly disabled
            if feed_name in self.disabled_feeds:
                logger.debug(f"Skipping disabled feed: {feed_name}")
                continue

            # Filter by enabled list if specified
            if self.enabled_feeds and feed_name not in self.enabled_feeds:
                logger.debug(f"Skipping non-enabled feed: {feed_name}")
                continue

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

        # Process each feed with per-feed configuration
        for (feed_name, feed_config), feed_data in zip(feeds_to_fetch.items(), feed_results):
            # Skip failed fetches
            if isinstance(feed_data, Exception) or feed_data is None:
                logger.warning(f"Skipping {feed_name} due to fetch failure")
                continue

            # Get per-feed configuration
            max_items = feed_config.get("max_items", 10)
            require_keyword_match = feed_config.get("require_keyword_match", False)
            return_top_n = feed_config.get("return_top_n", None)

            # Collect entries from this feed
            feed_items = []
            for entry in feed_data.entries[:max_items]:  # Limit to max_items
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

                # Apply keyword filtering if required
                if require_keyword_match and topic:
                    # Check if item matches keywords
                    if self._matches_keywords(result.title, keywords) or \
                       self._matches_keywords(result.snippet, keywords):
                        # Calculate relevance score for ranking
                        relevance = self._calculate_relevance_score(result, keywords)
                        feed_items.append((result, relevance))
                else:
                    # No keyword matching required, add all items
                    feed_items.append((result, 0.0))

            # Sort by relevance if keyword matching was applied
            if require_keyword_match and topic:
                feed_items.sort(key=lambda x: x[1], reverse=True)

            # Apply return_top_n limit if specified
            if return_top_n:
                feed_items = feed_items[:return_top_n]

            # Extract results (without scores)
            feed_results_only = [item[0] for item in feed_items]
            results.extend(feed_results_only)

            logger.info(f"Added {len(feed_results_only)} items from {feed_name}")

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
        Leverages per-feed configuration for smart filtering.

        Args:
            topic: Research topic
            days: Number of days back to fetch
            max_items: Maximum total items to return

        Returns:
            List of relevant SearchResult objects
        """
        logger.info(f"Fetching RSS feeds for topic: {topic}")

        # Use fetch_recent with topic-based filtering
        # This automatically handles per-feed configuration
        all_items = await self.fetch_recent(
            days=days,
            priority_filter=None,  # Fetch all priorities, per-feed config handles filtering
            topic=topic  # Pass topic for keyword matching
        )

        logger.info(f"Found {len(all_items)} relevant items for topic: {topic}")

        # Return top N most recent
        return all_items[:max_items]

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
