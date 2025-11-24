"""Enhanced search API clients (Serper, Tavily, Brave) with proper authentication.

Provides high-quality search results from multiple APIs with proper error handling,
rate limiting, and fallback support.
"""

import requests
import asyncio
import logging
from typing import List, Optional, Dict, Any
from src.state import SearchResult
from src.config import config

logger = logging.getLogger(__name__)


class SerperAPIClient:
    """Serper.dev API client for Google Search results."""

    def __init__(self, api_key: str):
        """Initialize Serper client.

        Args:
            api_key: Serper API key from https://serper.dev
        """
        self.api_key = api_key
        self.base_url = "https://google.serper.dev"
        self.timeout = 30

    async def search(self, query: str, max_results: int = 10, date_filter: Optional[str] = None) -> List[SearchResult]:
        """Search using Serper API.

        Args:
            query: Search query
            max_results: Maximum results to return
            date_filter: Date filter (qdr:d=day, qdr:w=week, qdr:m=month, qdr:y=year)

        Returns:
            List of SearchResult objects
        """
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }

            payload = {
                "q": query,
                "num": max_results
            }

            # Add date filter if specified
            if date_filter:
                payload["tbs"] = date_filter

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.base_url}/search",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
            )
            response.raise_for_status()

            data = response.json()
            results = []

            # Parse organic results
            for item in data.get("organic", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", "")
                ))

            logger.info(f"Serper: Found {len(results)} results for: {query[:50]}")
            return results

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Serper rate limit exceeded: {e}")
            elif e.response.status_code == 403:
                logger.error(f"Serper authentication failed - check API key")
            else:
                logger.error(f"Serper HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"Serper search error: {e}")
            return []


class TavilyAPIClient:
    """Tavily API client for research-focused search."""

    def __init__(self, api_key: str):
        """Initialize Tavily client.

        Args:
            api_key: Tavily API key from https://tavily.com
        """
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"
        self.timeout = 30

    async def search(self, query: str, max_results: int = 10, search_depth: str = "advanced") -> List[SearchResult]:
        """Search using Tavily API.

        Args:
            query: Search query
            max_results: Maximum results to return
            search_depth: Search depth ("basic" or "advanced")

        Returns:
            List of SearchResult objects
        """
        try:
            # IMPORTANT: Tavily uses Bearer token in Authorization header
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False
            }

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.base_url}/search",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
            )
            response.raise_for_status()

            data = response.json()
            results = []

            # Parse results
            for item in data.get("results", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")
                ))

            logger.info(f"Tavily: Found {len(results)} results for: {query[:50]}")
            return results

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Tavily rate limit exceeded: {e}")
            elif e.response.status_code == 401:
                logger.error(f"Tavily authentication failed - check API key and Bearer token format")
            else:
                logger.error(f"Tavily HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return []


class BraveAPIClient:
    """Brave Search API client."""

    def __init__(self, api_key: str):
        """Initialize Brave client.

        Args:
            api_key: Brave Search API key from https://brave.com/search/api/
        """
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.timeout = 30

    async def search(self, query: str, max_results: int = 10, freshness: Optional[str] = None) -> List[SearchResult]:
        """Search using Brave API.

        Args:
            query: Search query
            max_results: Maximum results to return
            freshness: Freshness filter (pd=day, pw=week, pm=month, py=year)

        Returns:
            List of SearchResult objects
        """
        try:
            headers = {
                "X-Subscription-Token": self.api_key,
                "Accept": "application/json"
            }

            params = {
                "q": query,
                "count": max_results
            }

            # Add freshness filter if specified
            if freshness:
                params["freshness"] = freshness

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
            )
            response.raise_for_status()

            data = response.json()
            results = []

            # Parse web results
            for item in data.get("web", {}).get("results", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", "")
                ))

            logger.info(f"Brave: Found {len(results)} results for: {query[:50]}")
            return results

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Brave rate limit exceeded: {e}")
            elif e.response.status_code == 401:
                logger.error(f"Brave authentication failed - check API key")
            else:
                logger.error(f"Brave HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return []


class MultiSearchClient:
    """Router for multiple search APIs with intelligent fallback."""

    def __init__(self):
        """Initialize multi-search client with configured APIs."""
        self.serper = None
        self.tavily = None
        self.brave = None

        # Initialize APIs if keys are provided and cloud APIs are enabled
        if config.enable_cloud_apis:
            if config.serper_api_key:
                self.serper = SerperAPIClient(config.serper_api_key)
                logger.info("Serper API initialized")

            if config.tavily_api_key:
                self.tavily = TavilyAPIClient(config.tavily_api_key)
                logger.info("Tavily API initialized")

            if config.brave_api_key:
                self.brave = BraveAPIClient(config.brave_api_key)
                logger.info("Brave API initialized")

        # Build available APIs list
        self.available_apis = []
        if self.serper:
            self.available_apis.append('serper')
        if self.tavily:
            self.available_apis.append('tavily')
        if self.brave:
            self.available_apis.append('brave')

        if not self.available_apis:
            logger.warning("No search APIs available - will use DuckDuckGo fallback")

    async def search(self, query: str, query_type: str = "general", max_results: int = 10) -> List[SearchResult]:
        """Search using the best API for the query type with fallback.

        Args:
            query: Search query
            query_type: Query type (news, research, statistics, general)
            max_results: Maximum results to return

        Returns:
            List of SearchResult objects
        """
        # Route by query type
        routing = {
            'news': ['serper', 'brave', 'tavily'],  # Serper best for news
            'research': ['tavily', 'serper', 'brave'],  # Tavily best for research/PDFs
            'statistics': ['serper', 'tavily', 'brave'],  # Serper best for .gov data
            'general': ['brave', 'serper', 'tavily']  # Brave as general fallback
        }

        api_priority = routing.get(query_type, routing['general'])

        # Try APIs in priority order
        for api_name in api_priority:
            if api_name not in self.available_apis:
                continue

            try:
                if api_name == 'serper' and self.serper:
                    # Add date filter for news queries
                    date_filter = "qdr:w" if query_type == 'news' else None
                    results = await self.serper.search(query, max_results, date_filter)
                    if results:
                        logger.info(f"✓ Used Serper for {query_type} query")
                        return results

                elif api_name == 'tavily' and self.tavily:
                    results = await self.tavily.search(query, max_results)
                    if results:
                        logger.info(f"✓ Used Tavily for {query_type} query")
                        return results

                elif api_name == 'brave' and self.brave:
                    # Add freshness filter for news queries
                    freshness = "pw" if query_type == 'news' else None
                    results = await self.brave.search(query, max_results, freshness)
                    if results:
                        logger.info(f"✓ Used Brave for {query_type} query")
                        return results

            except Exception as e:
                logger.warning(f"{api_name} failed, trying next API: {e}")
                continue

        # If all APIs failed, return empty (caller will use DuckDuckGo fallback)
        logger.warning(f"All search APIs failed for query: {query[:50]}")
        return []
