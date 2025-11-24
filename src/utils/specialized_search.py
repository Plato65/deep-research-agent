"""Specialized search tools for academic papers, forums, and consulting reports."""

import asyncio
import re
import time
from typing import List, Optional, Dict
from urllib.parse import quote_plus, urlparse
import requests
from bs4 import BeautifulSoup
import logging

from src.state import SearchResult
from src.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArxivSearch:
    """Search arXiv for academic papers."""

    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.last_search_time = 0
        self.min_delay = 3.0  # arXiv requests 3 second delay

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search arXiv for papers.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of SearchResult objects
        """
        try:
            # Rate limiting
            elapsed = time.time() - self.last_search_time
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)

            # Build query
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }

            logger.info(f"Searching arXiv for: {query}")

            response = await asyncio.to_thread(
                requests.get,
                self.base_url,
                params=params,
                timeout=config.web_request_timeout
            )
            response.raise_for_status()

            self.last_search_time = time.time()

            # Parse XML response
            soup = BeautifulSoup(response.content, 'xml')
            entries = soup.find_all('entry')

            results = []
            for entry in entries:
                title_elem = entry.find('title')
                summary_elem = entry.find('summary')
                id_elem = entry.find('id')

                if title_elem and id_elem:
                    title = title_elem.text.strip().replace('\n', ' ')
                    summary = summary_elem.text.strip().replace('\n', ' ') if summary_elem else ""
                    url = id_elem.text.strip()

                    results.append(SearchResult(
                        query=query,
                        title=title,
                        url=url,
                        snippet=summary[:300] + "..." if len(summary) > 300 else summary,
                        content=None
                    ))

            logger.info(f"Found {len(results)} arXiv results for: {query}")
            return results

        except Exception as e:
            logger.error(f"arXiv search error for '{query}': {str(e)}")
            return []


class SSRNSearch:
    """Search SSRN (Social Science Research Network) for papers."""

    def __init__(self):
        self.base_url = "https://papers.ssrn.com"
        self.search_url = f"{self.base_url}/sol3/topten/topTenResults.cfm"

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search SSRN for papers.

        Note: SSRN doesn't have a public API, so we use web scraping.
        This is best-effort and may break if SSRN changes their site.
        """
        try:
            logger.info(f"Searching SSRN for: {query}")

            # Use Google site search as fallback
            google_query = f"site:papers.ssrn.com {query}"
            from src.utils.web_utils import WebSearchTool

            search_tool = WebSearchTool(max_results=max_results)
            results = await search_tool.search_async(google_query)

            # Filter and format results
            ssrn_results = []
            for result in results:
                if 'ssrn.com' in result.url.lower():
                    ssrn_results.append(result)

            logger.info(f"Found {len(ssrn_results)} SSRN results for: {query}")
            return ssrn_results

        except Exception as e:
            logger.error(f"SSRN search error for '{query}': {str(e)}")
            return []


class HackerNewsSearch:
    """Search Hacker News using Algolia API."""

    def __init__(self):
        self.base_url = "https://hn.algolia.com/api/v1/search"
        self.last_search_time = 0
        self.min_delay = 1.0

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search Hacker News.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        try:
            # Rate limiting
            elapsed = time.time() - self.last_search_time
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)

            params = {
                'query': query,
                'tags': 'story',  # Only stories, not comments
                'hitsPerPage': max_results
            }

            logger.info(f"Searching Hacker News for: {query}")

            response = await asyncio.to_thread(
                requests.get,
                self.base_url,
                params=params,
                timeout=config.web_request_timeout
            )
            response.raise_for_status()

            self.last_search_time = time.time()

            data = response.json()
            hits = data.get('hits', [])

            results = []
            for hit in hits:
                title = hit.get('title', '')
                url = hit.get('url', '')

                # If no external URL, use HN discussion page
                if not url:
                    object_id = hit.get('objectID', '')
                    url = f"https://news.ycombinator.com/item?id={object_id}"

                # Get snippet from story text or first comment
                snippet = hit.get('story_text', '')
                if not snippet:
                    # Use title and author as snippet
                    author = hit.get('author', '')
                    points = hit.get('points', 0)
                    num_comments = hit.get('num_comments', 0)
                    snippet = f"By {author} | {points} points | {num_comments} comments"

                results.append(SearchResult(
                    query=query,
                    title=title,
                    url=url,
                    snippet=snippet[:300],
                    content=None
                ))

            logger.info(f"Found {len(results)} Hacker News results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Hacker News search error for '{query}': {str(e)}")
            return []


class RedditSearch:
    """Search Reddit for discussions."""

    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.use_api = bool(config.reddit_client_id and config.reddit_client_secret)

        if self.use_api:
            self._setup_api_client()

        self.last_search_time = 0
        self.min_delay = 2.0

    def _setup_api_client(self):
        """Setup Reddit API client if credentials provided."""
        try:
            import praw
            self.reddit = praw.Reddit(
                client_id=config.reddit_client_id,
                client_secret=config.reddit_client_secret,
                user_agent=config.reddit_user_agent
            )
            logger.info("Using Reddit API with authentication")
        except ImportError:
            logger.warning("praw not installed, falling back to web scraping")
            self.use_api = False
        except Exception as e:
            logger.warning(f"Reddit API setup failed: {e}, falling back to web scraping")
            self.use_api = False

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search Reddit.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        if self.use_api:
            return await self._search_api(query, max_results)
        else:
            return await self._search_web(query, max_results)

    async def _search_api(self, query: str, max_results: int) -> List[SearchResult]:
        """Search using Reddit API (PRAW)."""
        try:
            # Rate limiting
            elapsed = time.time() - self.last_search_time
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)

            logger.info(f"Searching Reddit (API) for: {query}")

            def search_reddit():
                submissions = list(self.reddit.subreddit("all").search(
                    query,
                    limit=max_results,
                    sort='relevance'
                ))
                return submissions

            submissions = await asyncio.to_thread(search_reddit)
            self.last_search_time = time.time()

            results = []
            for submission in submissions:
                results.append(SearchResult(
                    query=query,
                    title=submission.title,
                    url=f"https://www.reddit.com{submission.permalink}",
                    snippet=f"r/{submission.subreddit.display_name} | {submission.score} points | {submission.num_comments} comments | {submission.selftext[:200]}",
                    content=submission.selftext if submission.selftext else None
                ))

            logger.info(f"Found {len(results)} Reddit results for: {query}")
            return results

        except Exception as e:
            logger.error(f"Reddit API search error for '{query}': {str(e)}")
            return []

    async def _search_web(self, query: str, max_results: int) -> List[SearchResult]:
        """Search Reddit using Google site search."""
        try:
            logger.info(f"Searching Reddit (web) for: {query}")

            google_query = f"site:reddit.com {query}"
            from src.utils.web_utils import WebSearchTool

            search_tool = WebSearchTool(max_results=max_results)
            results = await search_tool.search_async(google_query)

            # Filter to only reddit URLs
            reddit_results = []
            for result in results:
                if 'reddit.com' in result.url.lower() and '/comments/' in result.url:
                    reddit_results.append(result)

            logger.info(f"Found {len(reddit_results)} Reddit results for: {query}")
            return reddit_results

        except Exception as e:
            logger.error(f"Reddit web search error for '{query}': {str(e)}")
            return []


class ConsultingReportSearch:
    """Search for consulting firm reports (McKinsey, BCG, Accenture, Deloitte, Bain)."""

    FIRMS = {
        'mckinsey': 'site:mckinsey.com/insights',
        'bcg': 'site:bcg.com/publications',
        'accenture': 'site:accenture.com/insights',
        'deloitte': 'site:deloitte.com/insights',
        'bain': 'site:bain.com/insights'
    }

    def __init__(self):
        self.last_search_time = 0
        self.min_delay = 2.0

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search consulting firm reports.

        Args:
            query: Search query
            max_results: Maximum results PER FIRM

        Returns:
            List of SearchResult objects
        """
        try:
            from src.utils.web_utils import WebSearchTool

            all_results = []
            results_per_firm = max(1, max_results // len(self.FIRMS))

            for firm_name, site_filter in self.FIRMS.items():
                # Rate limiting
                elapsed = time.time() - self.last_search_time
                if elapsed < self.min_delay:
                    await asyncio.sleep(self.min_delay - elapsed)

                # Remove mentions of other consulting firms from the query
                # This prevents silly searches like "McKinsey report" on BCG website
                cleaned_query = query
                for other_firm in ['mckinsey', 'bcg', 'accenture', 'deloitte', 'bain', 'pwc']:
                    # Remove firm name and common variations
                    cleaned_query = re.sub(rf'\b{other_firm}\b', '', cleaned_query, flags=re.IGNORECASE)
                    cleaned_query = re.sub(rf'\b{other_firm} report\b', '', cleaned_query, flags=re.IGNORECASE)
                    cleaned_query = re.sub(rf'\b{other_firm} analysis\b', '', cleaned_query, flags=re.IGNORECASE)

                # Clean up extra whitespace
                cleaned_query = ' '.join(cleaned_query.split())

                firm_query = f"{site_filter} {cleaned_query}"
                logger.info(f"Searching {firm_name.upper()} for: {cleaned_query}")

                search_tool = WebSearchTool(max_results=results_per_firm)
                results = await search_tool.search_async(firm_query)

                # Tag results with firm name
                for result in results:
                    result.snippet = f"[{firm_name.upper()}] {result.snippet}"
                    all_results.append(result)

                self.last_search_time = time.time()

            logger.info(f"Found {len(all_results)} consulting report results for: {query}")
            return all_results[:max_results]  # Limit total results

        except Exception as e:
            logger.error(f"Consulting report search error for '{query}': {str(e)}")
            return []


class AggregatedSearchTool:
    """Aggregates results from multiple specialized search tools."""

    def __init__(self):
        self.arxiv = ArxivSearch() if config.enable_arxiv_search else None
        self.ssrn = SSRNSearch() if config.enable_ssrn_search else None
        self.hackernews = HackerNewsSearch() if config.enable_hackernews_search else None
        self.reddit = RedditSearch() if config.enable_reddit_search else None
        self.consulting = ConsultingReportSearch() if config.detect_consulting_reports else None

    async def search_all(
        self,
        query: str,
        max_results_per_source: int = 5,
        sources: List[str] = None
    ) -> Dict[str, List[SearchResult]]:
        """Search across multiple specialized sources.

        Args:
            query: Search query
            max_results_per_source: Max results from each source
            sources: List of sources to search (None = all enabled)

        Returns:
            Dictionary mapping source name to list of results
        """
        available_sources = {
            'arxiv': self.arxiv,
            'ssrn': self.ssrn,
            'hackernews': self.hackernews,
            'reddit': self.reddit,
            'consulting': self.consulting
        }

        # Filter sources
        if sources:
            search_sources = {k: v for k, v in available_sources.items() if k in sources and v}
        else:
            search_sources = {k: v for k, v in available_sources.items() if v}

        logger.info(f"Searching {len(search_sources)} specialized sources for: {query}")

        # Run searches in parallel
        tasks = {}
        for source_name, search_tool in search_sources.items():
            tasks[source_name] = search_tool.search(query, max_results_per_source)

        results = {}
        for source_name, task in tasks.items():
            try:
                results[source_name] = await task
            except Exception as e:
                logger.error(f"Error searching {source_name}: {e}")
                results[source_name] = []

        total_results = sum(len(r) for r in results.values())
        logger.info(f"Total specialized search results: {total_results}")

        return results

    async def search_combined(
        self,
        query: str,
        max_total_results: int = 20,
        sources: List[str] = None
    ) -> List[SearchResult]:
        """Search all sources and return combined, deduplicated results.

        Args:
            query: Search query
            max_total_results: Maximum total results to return
            sources: List of sources to search (None = all enabled)

        Returns:
            Deduplicated list of SearchResult objects
        """
        results_by_source = await self.search_all(
            query,
            max_results_per_source=max(5, max_total_results // 4),
            sources=sources
        )

        # Combine all results
        all_results = []
        for source_name, source_results in results_by_source.items():
            all_results.extend(source_results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)

        # Limit results
        return unique_results[:max_total_results]
