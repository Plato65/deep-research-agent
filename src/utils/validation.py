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
