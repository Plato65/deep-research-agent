"""
Report Validation Module

Validates research reports for:
1. Citation integrity (no phantom citations)
2. Output cleanliness (no debug artifacts)
3. Source-mention matching (claims match references)
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from src.state import SearchResult

logger = logging.getLogger(__name__)


class CitationError(Exception):
    """Raised when citation integrity is violated."""
    pass


class ReportValidator:
    """Validates research reports for quality and integrity."""

    # Major sources that should be verified
    MAJOR_SOURCES = [
        'deloitte', 'bcg', 'gartner', 'mckinsey', 'brookings',
        'bls', 'bureau of labor', 'world bank', 'imf', 'oecd',
        'pew research', 'gallup', 'forrester', 'idc'
    ]

    # Debug patterns to remove
    DEBUG_PATTERNS = [
        r'validate_section_quality\s*\([^)]*\)',  # validate_section_quality(...)
        r'validate_citation\s*\([^)]*\)',          # validate_citation(...)
        r'check_quality\s*\([^)]*\)',              # check_quality(...)
        r'# DEBUG:.*?\n',                          # Debug comments
        r'print\s*\([^)]*\)\s*\n',                 # print statements
        r'logger\.debug\s*\([^)]*\)\s*\n',         # Debug logging
        r'```python.*?```',                         # Stray Python code blocks
        r'<thinking>.*?</thinking>',                # LLM thinking tags
        r'<internal>.*?</internal>',                # Internal notes
    ]

    def __init__(self):
        """Initialize report validator."""
        pass

    def extract_citations(self, text: str) -> set:
        """Extract all citation numbers from text.

        Args:
            text: Report text

        Returns:
            Set of citation numbers found
        """
        citations = set()
        # Match [1], [2], [10], etc.
        for match in re.finditer(r'\[(\d+)\]', text):
            citations.add(int(match.group(1)))
        return citations

    def validate_citations(
        self,
        report_text: str,
        sources: List[SearchResult],
        strict: bool = True
    ) -> Tuple[bool, List[str]]:
        """Validate that all citations in report have corresponding sources.

        Args:
            report_text: Full report text
            sources: List of SearchResult objects used in report
            strict: If True, raises CitationError on phantom citations

        Returns:
            Tuple of (is_valid, list of warnings/errors)
        """
        issues = []

        # Extract citations from text
        cited = self.extract_citations(report_text)

        # Available references (1-indexed)
        available = set(range(1, len(sources) + 1))

        # Find phantom citations
        phantoms = cited - available

        if phantoms:
            error_msg = (
                f"Report contains phantom citations {sorted(phantoms)}. "
                f"Only {len(sources)} references exist (1-{len(sources)}). "
                f"This indicates sources were cited but not included in final reference list."
            )
            issues.append(error_msg)

            if strict:
                raise CitationError(error_msg)

        # Find unused sources - warn if > 50% are unused (indicates over-fetching or poor filtering)
        unused = available - cited
        if unused and len(unused) > len(available) * 0.5:
            issues.append(
                f"Warning: {len(unused)} sources in reference list are not cited in text: {sorted(unused)}. "
                f"Consider reducing search results or improving source filtering."
            )

        # Check for sequential citation (optional - best practice)
        if cited:
            max_cited = max(cited)
            missing = set(range(1, max_cited + 1)) - cited
            if missing:
                issues.append(
                    f"Warning: Non-sequential citations. Missing: {sorted(missing)}"
                )

        return len(issues) == 0, issues

    def sanitize_output(self, text: str) -> str:
        """Remove debug artifacts and internal processing code from output.

        Args:
            text: Report text

        Returns:
            Cleaned text
        """
        cleaned = text

        # Apply all debug patterns
        for pattern in self.DEBUG_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Remove multiple blank lines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()

        return cleaned

    def validate_source_mentions(
        self,
        report_text: str,
        sources: List[SearchResult]
    ) -> List[str]:
        """Validate that major sources mentioned in text appear in references.

        Args:
            report_text: Full report text
            sources: List of SearchResult objects

        Returns:
            List of warnings for mentioned sources without references
        """
        warnings = []

        # Convert sources to lowercase text for matching
        source_text = ' '.join([
            s.url.lower() + ' ' + s.title.lower() + ' ' + s.snippet.lower()
            for s in sources
        ])

        report_lower = report_text.lower()

        # Check each major source
        for source_name in self.MAJOR_SOURCES:
            # Look for mentions like "Deloitte's 2024 analysis" or "according to BCG"
            patterns = [
                rf'\b{source_name}\b[\'`\u2019]s\s+(?:research|analysis|report|study|forecast)',
                rf'according to\s+{source_name}',
                rf'{source_name}\s+(?:reports|forecasts|projects|estimates|finds)',
                rf'research from\s+{source_name}',
                rf'{source_name}[\'`\u2019]s\s+modeling',
            ]

            mentioned = False
            for pattern in patterns:
                if re.search(pattern, report_lower):
                    mentioned = True
                    break

            if mentioned:
                # Check if source actually appears in references
                if source_name not in source_text:
                    warnings.append(
                        f"Report cites {source_name.title()} research but no matching reference found. "
                        f"This may be a hallucinated claim."
                    )

        return warnings

    def validate_report(
        self,
        report_text: str,
        sources: List[SearchResult],
        auto_sanitize: bool = True,
        strict_citations: bool = True
    ) -> Dict:
        """Run all validation checks on a report.

        Args:
            report_text: Full report text
            sources: List of SearchResult objects
            auto_sanitize: If True, automatically clean debug artifacts
            strict_citations: If True, raise error on phantom citations

        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'cleaned_report': str,
                'citation_valid': bool,
                'citation_issues': List[str],
                'source_warnings': List[str],
                'artifacts_removed': bool
            }

        Raises:
            CitationError: If strict_citations=True and phantom citations found
        """
        logger.info("Validating research report")

        # 1. Sanitize output
        cleaned_report = report_text
        artifacts_removed = False

        if auto_sanitize:
            cleaned_report = self.sanitize_output(report_text)
            artifacts_removed = (cleaned_report != report_text)

            if artifacts_removed:
                logger.warning("Debug artifacts found and removed from report")

        # 2. Validate citations
        citation_valid, citation_issues = self.validate_citations(
            cleaned_report,
            sources,
            strict=strict_citations
        )

        if not citation_valid:
            logger.error(f"Citation validation failed: {citation_issues}")

        # 3. Validate source mentions
        source_warnings = self.validate_source_mentions(cleaned_report, sources)

        if source_warnings:
            logger.warning(f"Source mention warnings: {source_warnings}")

        # Overall validity
        valid = citation_valid and len(source_warnings) == 0

        result = {
            'valid': valid,
            'cleaned_report': cleaned_report,
            'citation_valid': citation_valid,
            'citation_issues': citation_issues,
            'source_warnings': source_warnings,
            'artifacts_removed': artifacts_removed
        }

        # Log summary
        if valid:
            logger.info(
                "Report validation passed",
                extra={'validation_result': 'success'}
            )
        else:
            logger.warning(
                "Report validation issues detected",
                extra={
                    'validation_result': 'issues_found',
                    'citation_issues_count': len(citation_issues),
                    'source_warnings_count': len(source_warnings)
                }
            )

        return result

    def fix_phantom_citations(
        self,
        report_text: str,
        sources: List[SearchResult]
    ) -> str:
        """Attempt to automatically fix phantom citations by removing them.

        This is a last-resort function that removes citations that don't
        have corresponding sources. Use with caution as it may remove
        legitimate citations if sources were incorrectly filtered.

        Args:
            report_text: Report text with phantom citations
            sources: Available sources

        Returns:
            Report text with phantom citations removed
        """
        cited = self.extract_citations(report_text)
        available = set(range(1, len(sources) + 1))
        phantoms = cited - available

        if not phantoms:
            return report_text

        logger.warning(
            f"Removing phantom citations {sorted(phantoms)} from report. "
            f"This may indicate a bug in source filtering."
        )

        fixed = report_text
        for phantom in phantoms:
            # Remove [N] citations
            fixed = re.sub(rf'\[{phantom}\]', '', fixed)

        # Clean up multiple spaces and punctuation
        fixed = re.sub(r'\s+([.,;:])', r'\1', fixed)  # Remove space before punctuation
        fixed = re.sub(r'\s{2,}', ' ', fixed)          # Multiple spaces to single

        return fixed


# Convenience functions for direct use

def validate_report(
    report_text: str,
    sources: List[SearchResult],
    **kwargs
) -> Dict:
    """Validate a research report.

    See ReportValidator.validate_report for arguments and return value.
    """
    validator = ReportValidator()
    return validator.validate_report(report_text, sources, **kwargs)


def sanitize_report(report_text: str) -> str:
    """Remove debug artifacts from report text.

    Args:
        report_text: Report text to clean

    Returns:
        Cleaned report text
    """
    validator = ReportValidator()
    return validator.sanitize_output(report_text)


def check_citations(report_text: str, sources: List[SearchResult]) -> bool:
    """Quick check if citations are valid.

    Args:
        report_text: Report text
        sources: List of sources

    Returns:
        True if all citations are valid
    """
    validator = ReportValidator()
    valid, _ = validator.validate_citations(report_text, sources, strict=False)
    return valid
