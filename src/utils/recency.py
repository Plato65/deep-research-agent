"""Source recency detection and scoring."""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RecencyScorer:
    """Detect and score sources based on publication date/recency."""

    # Date patterns to look for in URLs, titles, and snippets
    DATE_PATTERNS = [
        # YYYY-MM-DD or YYYY/MM/DD
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
        # YYYY-MM or YYYY/MM
        r'(\d{4})[-/](\d{1,2})(?!\d)',
        # Month DD, YYYY or Mon DD, YYYY
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+(\d{1,2})[\s,]+(\d{4})',
        r'(January|February|March|April|May|June|July|August|September|October|November|December)[\s,]+(\d{1,2})[\s,]+(\d{4})',
        # Just year in path (e.g., /2024/)
        r'/(\d{4})/',
    ]

    MONTH_MAP = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12,
    }

    def __init__(self):
        self.current_date = datetime.now()
        self.current_year = self.current_date.year

    def extract_date(self, text: str) -> Optional[datetime]:
        """Extract the most recent date from text (URL, title, or snippet).

        Args:
            text: Text to search for dates

        Returns:
            datetime object if date found, None otherwise
        """
        if not text:
            return None

        text_lower = text.lower()
        found_dates = []

        try:
            # Try YYYY-MM-DD or YYYY/MM/DD
            match = re.search(self.DATE_PATTERNS[0], text)
            if match:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1900 <= year <= self.current_year and 1 <= month <= 12 and 1 <= day <= 31:
                    found_dates.append(datetime(year, month, day))

            # Try YYYY-MM or YYYY/MM (assume mid-month)
            if not found_dates:
                match = re.search(self.DATE_PATTERNS[1], text)
                if match:
                    year, month = int(match.group(1)), int(match.group(2))
                    if 1900 <= year <= self.current_year and 1 <= month <= 12:
                        found_dates.append(datetime(year, month, 15))

            # Try Month DD, YYYY
            if not found_dates:
                for pattern_idx in [2, 3]:
                    match = re.search(self.DATE_PATTERNS[pattern_idx], text_lower)
                    if match:
                        month_str = match.group(1).lower()
                        month = self.MONTH_MAP.get(month_str)
                        if month:
                            day = int(match.group(2))
                            year = int(match.group(3))
                            if 1900 <= year <= self.current_year and 1 <= day <= 31:
                                found_dates.append(datetime(year, month, day))
                                break

            # Try just year from path (least confident)
            if not found_dates:
                match = re.search(self.DATE_PATTERNS[4], text)
                if match:
                    year = int(match.group(1))
                    if 2000 <= year <= self.current_year:  # Only recent years
                        found_dates.append(datetime(year, 6, 30))  # Mid-year

            # Return most recent date if multiple found
            if found_dates:
                return max(found_dates)

        except Exception as e:
            logger.debug(f"Date extraction error: {e}")

        return None

    def score_recency(self, date: Optional[datetime]) -> Dict[str, Any]:
        """Score a date based on recency.

        Args:
            date: Publication date to score

        Returns:
            Dict with 'score' (0-20 bonus points), 'age_days', 'age_category'
        """
        if not date:
            return {
                'score': 0,
                'age_days': None,
                'age_category': 'unknown',
                'factor': 'No date found'
            }

        try:
            age = self.current_date - date
            age_days = age.days

            # Score based on age (max +20 points for recent content)
            if age_days < 0:
                # Future date - likely error, treat as recent
                score = 15
                category = 'very_recent'
                factor = 'Very recent (within 30 days)'
            elif age_days <= 30:
                score = 20  # Last month - maximum bonus
                category = 'very_recent'
                factor = 'Very recent (within 30 days)'
            elif age_days <= 90:
                score = 18  # Last 3 months
                category = 'recent'
                factor = 'Recent (within 3 months)'
            elif age_days <= 180:
                score = 15  # Last 6 months
                category = 'recent'
                factor = 'Recent (within 6 months)'
            elif age_days <= 365:
                score = 12  # Last year
                category = 'current_year'
                factor = 'Current year'
            elif age_days <= 730:
                score = 8   # Last 2 years
                category = 'recent_past'
                factor = 'Within 2 years'
            elif age_days <= 1095:
                score = 5   # Last 3 years
                category = 'recent_past'
                factor = 'Within 3 years'
            elif age_days <= 1825:
                score = 2   # Last 5 years
                category = 'older'
                factor = 'Within 5 years'
            else:
                score = 0   # Older than 5 years - no bonus
                category = 'old'
                factor = f'Older content ({age_days // 365} years old)'

            return {
                'score': score,
                'age_days': age_days,
                'age_category': category,
                'factor': factor,
                'date': date.strftime('%Y-%m-%d')
            }

        except Exception as e:
            logger.warning(f"Recency scoring error: {e}")
            return {
                'score': 0,
                'age_days': None,
                'age_category': 'error',
                'factor': 'Error calculating recency'
            }

    def score_source_recency(self, url: str, title: str = "", snippet: str = "") -> Dict[str, Any]:
        """Score a source's recency by extracting dates from URL, title, and snippet.

        Args:
            url: Source URL
            title: Source title
            snippet: Source snippet/description

        Returns:
            Dict with recency score and details
        """
        # Try to extract date from multiple sources (prioritize URL, then title, then snippet)
        date = None
        found_in = None

        # Check URL first (most reliable for date-based paths)
        date = self.extract_date(url)
        if date:
            found_in = 'url'

        # Check title if not found in URL
        if not date and title:
            date = self.extract_date(title)
            if date:
                found_in = 'title'

        # Check snippet if still not found
        if not date and snippet:
            date = self.extract_date(snippet)
            if date:
                found_in = 'snippet'

        # Score the recency
        result = self.score_recency(date)
        result['found_in'] = found_in

        return result
