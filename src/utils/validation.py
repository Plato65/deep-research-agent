"""Input validation and sanitization utilities."""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """Validates and sanitizes user inputs."""

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'on\w+\s*=',  # Event handlers (onclick, onload, etc.)
        r'eval\s*\(',  # Eval function
        r'exec\s*\(',  # Exec function
        r'\.\./|\.\.\\',  # Path traversal
        r'[\x00-\x1f\x7f-\x9f]',  # Control characters
    ]

    # Maximum lengths for various inputs
    MAX_TOPIC_LENGTH = 500
    MAX_URL_LENGTH = 2048
    MIN_TOPIC_LENGTH = 3

    @staticmethod
    def sanitize_research_topic(topic: str) -> Tuple[bool, str, Optional[str]]:
        """Sanitize and validate a research topic.

        Args:
            topic: The research topic to validate

        Returns:
            Tuple of (is_valid, sanitized_topic, error_message)
        """
        if not topic or not topic.strip():
            return False, "", "Research topic cannot be empty"

        # Strip whitespace
        topic = topic.strip()

        # Check length
        if len(topic) < InputValidator.MIN_TOPIC_LENGTH:
            return False, topic, f"Research topic must be at least {InputValidator.MIN_TOPIC_LENGTH} characters"

        if len(topic) > InputValidator.MAX_TOPIC_LENGTH:
            return False, topic, f"Research topic must be less than {InputValidator.MAX_TOPIC_LENGTH} characters"

        # Check for dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, topic, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected in topic: {pattern}")
                return False, topic, "Research topic contains invalid characters or patterns"

        # Remove excessive whitespace
        topic = re.sub(r'\s+', ' ', topic)

        # Basic sanitization - remove HTML tags
        topic = re.sub(r'<[^>]+>', '', topic)

        # Remove any remaining control characters
        topic = ''.join(char for char in topic if ord(char) >= 32 or char in '\n\t')

        return True, topic, None

    @staticmethod
    def sanitize_url(url: str) -> Tuple[bool, str, Optional[str]]:
        """Sanitize and validate a URL.

        Args:
            url: The URL to validate

        Returns:
            Tuple of (is_valid, sanitized_url, error_message)
        """
        if not url or not url.strip():
            return False, "", "URL cannot be empty"

        url = url.strip()

        # Check length
        if len(url) > InputValidator.MAX_URL_LENGTH:
            return False, url, f"URL must be less than {InputValidator.MAX_URL_LENGTH} characters"

        # Check for dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected in URL: {pattern}")
                return False, url, "URL contains invalid patterns"

        # Parse URL
        try:
            parsed = urlparse(url)

            # Validate scheme
            if parsed.scheme and parsed.scheme.lower() not in ['http', 'https', 'ftp']:
                return False, url, f"Invalid URL scheme: {parsed.scheme}. Only http, https, and ftp are allowed"

            # Validate netloc (domain) is present
            if not parsed.netloc:
                return False, url, "URL must have a valid domain"

            # Reconstruct clean URL
            clean_url = urlunparse((
                parsed.scheme.lower() if parsed.scheme else 'https',
                parsed.netloc.lower(),
                parsed.path,
                parsed.params,
                parsed.query,
                ''  # Remove fragment
            ))

            return True, clean_url, None

        except Exception as e:
            logger.error(f"URL parsing error: {e}")
            return False, url, f"Invalid URL format: {str(e)}"

    @staticmethod
    def validate_search_query(query: str) -> Tuple[bool, str, Optional[str]]:
        """Validate a search query.

        Args:
            query: The search query to validate

        Returns:
            Tuple of (is_valid, sanitized_query, error_message)
        """
        if not query or not query.strip():
            return False, "", "Search query cannot be empty"

        query = query.strip()

        # Check length
        if len(query) < 2:
            return False, query, "Search query must be at least 2 characters"

        if len(query) > 500:
            return False, query, "Search query must be less than 500 characters"

        # Remove excessive whitespace
        query = re.sub(r'\s+', ' ', query)

        # Basic sanitization
        query = re.sub(r'<[^>]+>', '', query)

        return True, query, None

    @staticmethod
    def validate_file_path(path: str, allowed_extensions: Optional[list] = None) -> Tuple[bool, str, Optional[str]]:
        """Validate a file path.

        Args:
            path: The file path to validate
            allowed_extensions: List of allowed file extensions (e.g., ['.pdf', '.md'])

        Returns:
            Tuple of (is_valid, sanitized_path, error_message)
        """
        if not path or not path.strip():
            return False, "", "File path cannot be empty"

        path = path.strip()

        # Check for path traversal
        if '..' in path or path.startswith('/'):
            return False, path, "Invalid file path: path traversal detected"

        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        for char in dangerous_chars:
            if char in path:
                return False, path, f"Invalid file path: contains dangerous character '{char}'"

        # Check extension if specified
        if allowed_extensions:
            ext = path[path.rfind('.'):] if '.' in path else ''
            if ext.lower() not in [e.lower() for e in allowed_extensions]:
                return False, path, f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"

        return True, path, None


class URLSanitizer:
    """Advanced URL sanitization and validation."""

    @staticmethod
    def is_safe_url(url: str) -> bool:
        """Check if a URL is safe to fetch.

        Args:
            url: URL to check

        Returns:
            True if URL is safe, False otherwise
        """
        try:
            parsed = urlparse(url)

            # Block localhost and private IPs
            blocked_hosts = [
                'localhost',
                '127.0.0.1',
                '0.0.0.0',
                '::1',
            ]

            if parsed.netloc.lower() in blocked_hosts:
                logger.warning(f"Blocked localhost/private URL: {url}")
                return False

            # Block private IP ranges
            if parsed.netloc.startswith('10.') or \
               parsed.netloc.startswith('192.168.') or \
               parsed.netloc.startswith('172.16.') or \
               parsed.netloc.startswith('172.31.'):
                logger.warning(f"Blocked private IP URL: {url}")
                return False

            # Block file:// protocol
            if parsed.scheme == 'file':
                logger.warning(f"Blocked file:// protocol: {url}")
                return False

            return True

        except Exception as e:
            logger.error(f"URL safety check error: {e}")
            return False

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize a URL to canonical form.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL
        """
        try:
            parsed = urlparse(url)

            # Ensure scheme
            if not parsed.scheme:
                url = 'https://' + url
                parsed = urlparse(url)

            # Lowercase scheme and netloc
            normalized = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path,
                parsed.params,
                parsed.query,
                ''  # Remove fragment
            ))

            # Remove trailing slash from path (unless it's the root)
            if normalized.endswith('/') and parsed.path != '/':
                normalized = normalized[:-1]

            return normalized

        except Exception:
            return url


# Convenience functions
def validate_topic(topic: str) -> Tuple[bool, str, Optional[str]]:
    """Validate research topic - convenience wrapper."""
    return InputValidator.sanitize_research_topic(topic)


def validate_url(url: str) -> Tuple[bool, str, Optional[str]]:
    """Validate URL - convenience wrapper."""
    return InputValidator.sanitize_url(url)


def is_safe_url(url: str) -> bool:
    """Check if URL is safe - convenience wrapper."""
    return URLSanitizer.is_safe_url(url)


class ResearchStateValidator:
    """Validates ResearchState objects for agent operations."""

    @staticmethod
    def validate_state_for_search(state) -> Tuple[bool, Optional[str]]:
        """Validate state has required fields for search operation.

        Args:
            state: ResearchState to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate topic
        valid, _, error = InputValidator.sanitize_research_topic(state.research_topic)
        if not valid:
            return False, error

        # Validate plan exists
        if not state.plan:
            return False, "No research plan available - cannot perform search"

        # Validate plan has search queries
        if not hasattr(state.plan, 'search_queries') or not state.plan.search_queries:
            return False, "Research plan missing search queries"

        if len(state.plan.search_queries) == 0:
            return False, "Research plan has zero search queries"

        return True, None

    @staticmethod
    def validate_state_for_synthesis(state) -> Tuple[bool, Optional[str]]:
        """Validate state has required fields for synthesis operation.

        Args:
            state: ResearchState to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not state.research_topic:
            return False, "Missing research topic"

        if not state.search_results:
            return False, "No search results available for synthesis"

        if len(state.search_results) == 0:
            return False, "Search results list is empty"

        return True, None

    @staticmethod
    def validate_state_for_writing(state) -> Tuple[bool, Optional[str]]:
        """Validate state has required fields for report writing.

        Args:
            state: ResearchState to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not state.research_topic:
            return False, "Missing research topic"

        if not state.plan:
            return False, "Missing research plan"

        if not state.key_findings:
            return False, "Missing key findings - cannot write report"

        if not state.search_results:
            return False, "Missing search results for citations"

        return True, None


class SearchResultValidator:
    """Validates search results."""

    @staticmethod
    def validate_single_result(result, index: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """Validate a single search result.

        Args:
            result: SearchResult to validate
            index: Optional index for error reporting

        Returns:
            Tuple of (is_valid, error_message)

        Checks:
        - Has url attribute
        - Has title attribute
        - URL is valid
        - Title is not empty
        """
        prefix = f"Result {index}: " if index is not None else ""

        # Check required attributes
        if not hasattr(result, 'url'):
            return False, f"{prefix}Missing 'url' attribute"

        if not hasattr(result, 'title'):
            return False, f"{prefix}Missing 'title' attribute"

        # Validate URL
        valid, _, error = InputValidator.sanitize_url(result.url)
        if not valid:
            return False, f"{prefix}{error}"

        # Validate title
        if not result.title or not result.title.strip():
            return False, f"{prefix}Title is empty"

        return True, None

    @staticmethod
    def validate_results_batch(
        results: list,
        check_duplicates: bool = True,
        min_results: int = 1
    ) -> Tuple[bool, list]:
        """Validate a batch of search results.

        Args:
            results: List of SearchResult objects to validate
            check_duplicates: Whether to check for duplicate URLs
            min_results: Minimum number of results required

        Returns:
            Tuple of (is_valid, list_of_errors)
            Empty error list if valid

        Checks:
        - List is not empty (if min_results > 0)
        - Each result is valid
        - No duplicate URLs (if check_duplicates=True)
        - Meets minimum result count
        """
        errors = []

        # Check if list exists and meets minimum
        if not results:
            if min_results > 0:
                errors.append(f"Results list is empty (minimum {min_results} required)")
            return len(errors) == 0, errors

        if len(results) < min_results:
            errors.append(
                f"Insufficient results: {len(results)} found, {min_results} required"
            )

        # Validate each result
        seen_urls = set()
        for i, result in enumerate(results):
            valid, error = SearchResultValidator.validate_single_result(result, index=i)
            if not valid:
                errors.append(error)
                continue

            # Check for duplicates
            if check_duplicates and hasattr(result, 'url'):
                if result.url in seen_urls:
                    errors.append(f"Result {i}: Duplicate URL: {result.url}")
                seen_urls.add(result.url)

        return len(errors) == 0, errors


class ConfigurationValidator:
    """Validates configuration settings."""

    @staticmethod
    def validate_model_config(config) -> list:
        """Validate model configuration.

        Args:
            config: Configuration object to validate

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        # Check provider-specific requirements
        if config.model_provider == "openai":
            if not config.openai_api_key or config.openai_api_key == "your-api-key-here":
                warnings.append("OpenAI provider selected but no valid API key configured")

        elif config.model_provider == "anthropic":
            if not config.anthropic_api_key or config.anthropic_api_key == "your-api-key-here":
                warnings.append("Anthropic provider selected but no valid API key configured")

        elif config.model_provider == "gemini":
            if not config.gemini_api_key or config.gemini_api_key == "your-api-key-here":
                warnings.append("Gemini provider selected but no valid API key configured")

        elif config.model_provider == "ollama":
            if not config.ollama_base_url:
                warnings.append("Ollama provider selected but no base URL configured")

        elif config.model_provider == "lmstudio":
            if not config.lmstudio_base_url:
                warnings.append("LM Studio provider selected but no base URL configured")

        # Check specialized model configs
        if config.use_dr_tulu_writer:
            if not config.dr_tulu_endpoint:
                warnings.append("DR Tulu writer enabled but no endpoint configured")
            if not config.dr_tulu_model_name and config.model_provider == "lmstudio":
                warnings.append(
                    "DR Tulu writer with LM Studio requires dr_tulu_model_name to be set"
                )

        if config.use_olmo_critic:
            if not config.olmo_endpoint:
                warnings.append("OLMo critic enabled but no endpoint configured")
            if not config.olmo_model_name and config.model_provider == "lmstudio":
                warnings.append(
                    "OLMo critic with LM Studio requires olmo_model_name to be set"
                )

        return warnings

    @staticmethod
    def validate_search_config(config) -> list:
        """Validate search configuration.

        Args:
            config: Configuration object to validate

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        # Check Reddit config
        if config.enable_reddit_search:
            if not config.reddit_client_id or not config.reddit_client_secret:
                warnings.append(
                    "Reddit search enabled but credentials not configured. "
                    "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET or disable with "
                    "ENABLE_REDDIT_SEARCH=false"
                )

        # Check RSS config
        if config.enable_rss_feeds:
            if not config.enabled_rss_feeds and not config.custom_rss_feeds:
                warnings.append(
                    "RSS feeds enabled but no feeds configured. "
                    "Will use default priority filter: " +
                    (config.rss_priority_filter or "all")
                )

        # Check search API availability
        has_search_api = any([
            config.serper_api_key and config.serper_api_key != "your-api-key-here",
            config.tavily_api_key and config.tavily_api_key != "your-api-key-here",
            config.brave_api_key and config.brave_api_key != "your-api-key-here",
            config.enable_duckduckgo_search
        ])

        if not has_search_api:
            warnings.append(
                "No search API configured. Please set at least one: "
                "SERPER_API_KEY, TAVILY_API_KEY, BRAVE_API_KEY, or enable DuckDuckGo"
            )

        return warnings


def validate_json_structure(data, expected_keys: list) -> Tuple[bool, Optional[str]]:
    """Validate JSON structure has expected keys.

    Args:
        data: Parsed JSON data
        expected_keys: List of keys that must be present

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> validate_json_structure({"foo": 1}, ["foo", "bar"])
        (False, "Missing required keys: bar")
    """
    if not isinstance(data, dict):
        return False, f"Expected dict, got {type(data).__name__}"

    missing_keys = [key for key in expected_keys if key not in data]

    if missing_keys:
        return False, f"Missing required keys: {', '.join(missing_keys)}"

    return True, None
