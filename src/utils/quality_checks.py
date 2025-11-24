"""Quality validation system for research reports.

Provides citation verification, hallucination detection, and freshness checking
to ensure report quality before publication.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse
from src.state import SearchResult

logger = logging.getLogger(__name__)


class QualityValidator:
    """Validates research report quality through multiple checks."""

    def __init__(self):
        """Initialize quality validator."""
        self.citation_pattern = re.compile(r'\[(\d+)\]')
        self.url_pattern = re.compile(r'https?://[^\s\)]+')

    async def verify_citations(
        self,
        report: str,
        sources: List[SearchResult]
    ) -> Dict[str, Any]:
        """Verify that citations in report reference valid sources.

        Args:
            report: The generated report text (markdown)
            sources: List of search results used

        Returns:
            Dictionary with verification results:
            {
                "valid_citations": int,
                "invalid_citations": List[int],
                "uncited_sources": List[str],
                "citation_coverage": float (0-100),
                "issues": List[str]
            }
        """
        logger.info("Starting citation verification")

        # Extract all citation numbers from report
        citations = self.citation_pattern.findall(report)
        citation_numbers = [int(c) for c in citations]
        unique_citations = set(citation_numbers)

        # Build source index from references section
        source_urls = self._extract_source_urls(report)

        # Check for invalid citations
        invalid_citations = []
        max_valid_citation = len(source_urls)

        for cite_num in unique_citations:
            if cite_num < 1 or cite_num > max_valid_citation:
                invalid_citations.append(cite_num)

        # Check for uncited sources
        cited_indices = set(range(1, max_valid_citation + 1))
        uncited_indices = cited_indices - unique_citations
        uncited_sources = [source_urls[i-1] for i in uncited_indices if i-1 < len(source_urls)]

        # Calculate coverage
        citation_coverage = (len(unique_citations) / len(source_urls) * 100) if source_urls else 0

        # Generate issues list
        issues = []
        if invalid_citations:
            issues.append(f"Invalid citations found: {invalid_citations}")
        if uncited_sources:
            issues.append(f"{len(uncited_sources)} sources listed but never cited")
        if citation_coverage < 50:
            issues.append(f"Low citation coverage: {citation_coverage:.1f}%")

        result = {
            "valid_citations": len(unique_citations) - len(invalid_citations),
            "total_citations": len(citation_numbers),
            "invalid_citations": invalid_citations,
            "uncited_sources": uncited_sources[:5],  # First 5 only
            "citation_coverage": round(citation_coverage, 1),
            "issues": issues,
            "passed": len(issues) == 0
        }

        logger.info(
            f"Citation verification: {result['valid_citations']}/{result['total_citations']} valid, "
            f"{citation_coverage:.1f}% coverage, {len(issues)} issues"
        )

        return result

    async def detect_hallucinations(
        self,
        report: str,
        sources: List[SearchResult],
        min_citations_per_section: int = 2
    ) -> Dict[str, Any]:
        """Detect potential hallucinations (unsupported claims).

        Identifies sentences making factual claims without citations, which could
        indicate hallucinated content not backed by sources.

        Args:
            report: The generated report text (markdown)
            sources: List of search results used
            min_citations_per_section: Minimum citations required per section

        Returns:
            Dictionary with hallucination detection results:
            {
                "unsupported_claims": List[str],
                "sections_below_threshold": List[str],
                "hallucination_risk": str (low/medium/high),
                "issues": List[str]
            }
        """
        logger.info("Starting hallucination detection")

        # Split report into sections
        sections = self._split_into_sections(report)

        unsupported_claims = []
        sections_below_threshold = []

        for section_title, section_content in sections:
            # Skip introduction and conclusion (less citation-heavy)
            if any(skip in section_title.lower() for skip in ['introduction', 'conclusion', 'summary']):
                continue

            # Count citations in section
            citations = self.citation_pattern.findall(section_content)
            citation_count = len(citations)

            if citation_count < min_citations_per_section:
                sections_below_threshold.append(section_title)

            # Find sentences making factual claims without citations
            sentences = self._extract_sentences(section_content)
            for sentence in sentences:
                if self._is_factual_claim(sentence) and '[' not in sentence:
                    unsupported_claims.append(sentence[:150])  # Truncate long sentences

        # Calculate risk level
        total_sections = len([s for s in sections if 'introduction' not in s[0].lower() and 'conclusion' not in s[0].lower()])
        risk_ratio = len(sections_below_threshold) / max(total_sections, 1)

        if risk_ratio > 0.5 or len(unsupported_claims) > 10:
            risk_level = "high"
        elif risk_ratio > 0.25 or len(unsupported_claims) > 5:
            risk_level = "medium"
        else:
            risk_level = "low"

        issues = []
        if unsupported_claims:
            issues.append(f"{len(unsupported_claims)} sentences with unsupported claims")
        if sections_below_threshold:
            issues.append(f"{len(sections_below_threshold)} sections below citation threshold")

        result = {
            "unsupported_claims": unsupported_claims[:10],  # First 10 only
            "sections_below_threshold": sections_below_threshold,
            "hallucination_risk": risk_level,
            "issues": issues,
            "passed": risk_level == "low"
        }

        logger.info(
            f"Hallucination detection: {len(unsupported_claims)} unsupported claims, "
            f"{len(sections_below_threshold)} sections below threshold, risk={risk_level}"
        )

        return result

    async def check_freshness(
        self,
        sources: List[SearchResult],
        max_age_days: int = 365,
        min_recent_sources: int = 3
    ) -> Dict[str, Any]:
        """Verify sources meet recency requirements.

        Args:
            sources: List of search results
            max_age_days: Maximum age in days for sources
            min_recent_sources: Minimum number of recent sources required

        Returns:
            Dictionary with freshness check results:
            {
                "recent_sources": int,
                "old_sources": int,
                "oldest_date": str,
                "freshness_score": float (0-100),
                "issues": List[str]
            }
        """
        logger.info(f"Starting freshness check (max_age={max_age_days} days)")

        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        recent_sources = []
        old_sources = []
        dates_found = []

        for source in sources:
            # Try to extract date from URL or title
            source_date = self._extract_date(source)

            if source_date:
                dates_found.append(source_date)
                if source_date >= cutoff_date:
                    recent_sources.append(source)
                else:
                    old_sources.append(source)
            else:
                # Unknown date - assume recent for benefit of doubt
                recent_sources.append(source)

        # Calculate freshness score
        total_with_dates = len(dates_found)
        if total_with_dates > 0:
            recent_ratio = len([d for d in dates_found if d >= cutoff_date]) / total_with_dates
            freshness_score = recent_ratio * 100
        else:
            # No dates found - give neutral score
            freshness_score = 50.0

        # Find oldest source
        oldest_date = min(dates_found).strftime("%Y-%m-%d") if dates_found else "Unknown"

        # Generate issues
        issues = []
        if len(recent_sources) < min_recent_sources:
            issues.append(f"Only {len(recent_sources)} recent sources (need {min_recent_sources})")
        if freshness_score < 50:
            issues.append(f"Low freshness score: {freshness_score:.1f}%")
        if len(old_sources) > len(recent_sources):
            issues.append(f"More old sources ({len(old_sources)}) than recent ({len(recent_sources)})")

        result = {
            "recent_sources": len(recent_sources),
            "old_sources": len(old_sources),
            "sources_with_dates": len(dates_found),
            "oldest_date": oldest_date,
            "freshness_score": round(freshness_score, 1),
            "issues": issues,
            "passed": len(issues) == 0
        }

        logger.info(
            f"Freshness check: {len(recent_sources)} recent, {len(old_sources)} old, "
            f"score={freshness_score:.1f}%, {len(issues)} issues"
        )

        return result

    async def validate_report(
        self,
        report: str,
        sources: List[SearchResult],
        mode: str = "general",
        strict: bool = False
    ) -> Dict[str, Any]:
        """Run all quality checks on a report.

        Args:
            report: The generated report text
            sources: List of search results used
            mode: Research mode (weekly/general/privacy)
            strict: If True, fail on any issues

        Returns:
            Dictionary with all validation results:
            {
                "passed": bool,
                "overall_score": float (0-100),
                "citations": Dict,
                "hallucinations": Dict,
                "freshness": Dict,
                "issues": List[str]
            }
        """
        logger.info(f"Running full quality validation (mode={mode}, strict={strict})")

        # Run all checks
        citation_results = await self.verify_citations(report, sources)
        hallucination_results = await self.detect_hallucinations(report, sources)

        # Adjust freshness check based on mode
        if mode == "weekly":
            freshness_results = await self.check_freshness(sources, max_age_days=14, min_recent_sources=5)
        elif mode == "general":
            freshness_results = await self.check_freshness(sources, max_age_days=365, min_recent_sources=3)
        else:  # privacy
            freshness_results = await self.check_freshness(sources, max_age_days=365, min_recent_sources=2)

        # Calculate overall score (weighted average)
        citation_score = citation_results.get("citation_coverage", 0)
        hallucination_score = 100 if hallucination_results["hallucination_risk"] == "low" else (
            50 if hallucination_results["hallucination_risk"] == "medium" else 0
        )
        freshness_score = freshness_results.get("freshness_score", 0)

        overall_score = (
            citation_score * 0.4 +
            hallucination_score * 0.4 +
            freshness_score * 0.2
        )

        # Determine pass/fail
        all_checks_passed = (
            citation_results["passed"] and
            hallucination_results["passed"] and
            freshness_results["passed"]
        )

        if strict:
            passed = all_checks_passed
        else:
            passed = overall_score >= 60  # Passing threshold

        # Collect all issues
        all_issues = (
            citation_results.get("issues", []) +
            hallucination_results.get("issues", []) +
            freshness_results.get("issues", [])
        )

        result = {
            "passed": passed,
            "overall_score": round(overall_score, 1),
            "citations": citation_results,
            "hallucinations": hallucination_results,
            "freshness": freshness_results,
            "issues": all_issues,
            "mode": mode,
            "strict": strict
        }

        logger.info(
            f"Quality validation complete: {'PASSED' if passed else 'FAILED'}, "
            f"score={overall_score:.1f}/100, {len(all_issues)} issues"
        )

        return result

    # Helper methods

    def _extract_source_urls(self, report: str) -> List[str]:
        """Extract source URLs from references section."""
        urls = []

        # Find references section
        refs_match = re.search(r'##\s+References\s*\n(.*?)(?:\n##|$)', report, re.DOTALL | re.IGNORECASE)
        if refs_match:
            refs_section = refs_match.group(1)
            # Extract URLs from markdown links
            url_matches = re.findall(r'\[.*?\]\((https?://[^\)]+)\)', refs_section)
            urls.extend(url_matches)

        return urls

    def _split_into_sections(self, report: str) -> List[Tuple[str, str]]:
        """Split report into sections."""
        sections = []

        # Split by ## headers
        parts = re.split(r'\n##\s+([^\n]+)\n', report)

        # First part is before any headers
        if parts[0].strip():
            sections.append(("Introduction", parts[0]))

        # Pair up headers and content
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                title = parts[i].strip()
                content = parts[i + 1].strip()
                sections.append((title, content))

        return sections

    def _extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text."""
        # Remove markdown formatting
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Links
        text = re.sub(r'[*_`#]', '', text)  # Formatting

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        # Filter out short fragments and headers
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        return sentences

    def _is_factual_claim(self, sentence: str) -> bool:
        """Determine if sentence makes a factual claim requiring citation."""
        # Skip questions
        if '?' in sentence:
            return False

        # Skip meta statements about the report itself
        meta_phrases = [
            'this report', 'this section', 'we will', 'we examine',
            'below we', 'following section', 'as shown'
        ]
        if any(phrase in sentence.lower() for phrase in meta_phrases):
            return False

        # Look for factual claim indicators
        claim_indicators = [
            'research shows', 'study found', 'according to', 'data shows',
            'results indicate', 'analysis reveals', 'reported that',
            'demonstrates that', 'suggests that', 'found that',
            'in 20', 'percent', '%', 'million', 'billion',
            'increased', 'decreased', 'grew', 'declined'
        ]

        return any(indicator in sentence.lower() for indicator in claim_indicators)

    def _extract_date(self, source: SearchResult) -> Optional[datetime]:
        """Extract date from source URL or title."""
        # Try URL path (e.g., /2024/01/article)
        url_match = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})', source.url)
        if url_match:
            try:
                year, month, day = map(int, url_match.groups())
                return datetime(year, month, day)
            except ValueError:
                pass

        # Try URL path (e.g., /2024/article)
        url_match = re.search(r'/(\d{4})/[^/]+$', source.url)
        if url_match:
            try:
                year = int(url_match.group(1))
                return datetime(year, 1, 1)
            except ValueError:
                pass

        # Try title (e.g., "Article Title (2024)")
        title_match = re.search(r'\((\d{4})\)', source.title)
        if title_match:
            try:
                year = int(title_match.group(1))
                return datetime(year, 1, 1)
            except ValueError:
                pass

        # Try snippet for date mentions
        snippet_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(\d{4})', source.snippet)
        if snippet_match:
            try:
                date_str = snippet_match.group(0)
                return datetime.strptime(date_str.replace(',', ''), "%B %d %Y")
            except ValueError:
                pass

        return None
