"""
Unit tests for report validation module.

Tests citation integrity, output sanitization, and source-mention validation.
"""

import pytest
from src.utils.report_validator import ReportValidator, CitationError
from src.state import SearchResult


class TestReportValidator:
    """Test suite for ReportValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ReportValidator()

        # Sample sources for testing
        self.sources = [
            SearchResult(
                query="AI automation impact on jobs",
                url="https://www.mckinsey.com/report1",
                title="Jobs lost, jobs gained",
                snippet="McKinsey research on AI automation",
                content="Detailed analysis of automation impact"
            ),
            SearchResult(
                query="hybrid jobs in finance",
                url="https://www.brookings.edu/article1",
                title="Hybrid jobs in finance",
                snippet="Brookings study on AI in finance",
                content="Financial sector transformation"
            ),
            SearchResult(
                query="AI job matching systems",
                url="https://arxiv.org/abs/2024.12345",
                title="Deep learning for job matching",
                snippet="LinkedIn research paper",
                content="AI-driven recruitment systems"
            ),
        ]

    def test_extract_citations(self):
        """Test citation extraction from text."""
        text = "According to research [1], AI is transforming work [2][3]. See also [10]."

        citations = self.validator.extract_citations(text)

        assert citations == {1, 2, 3, 10}

    def test_extract_citations_empty(self):
        """Test citation extraction with no citations."""
        text = "This text has no citations at all."

        citations = self.validator.extract_citations(text)

        assert citations == set()

    def test_validate_citations_valid(self):
        """Test validation with all valid citations."""
        report = """
        According to McKinsey [1], AI will transform 57% of work hours.
        Brookings research [2] shows hybrid jobs emerging.
        LinkedIn's deep learning models [3] improve job matching.
        """

        valid, issues = self.validator.validate_citations(
            report,
            self.sources,
            strict=False
        )

        assert valid
        assert len(issues) == 0

    def test_validate_citations_phantom(self):
        """Test validation with phantom citations."""
        report = """
        According to McKinsey [1], AI will transform work.
        Research shows [5] that jobs will change.
        Other studies [10] confirm this trend.
        """

        valid, issues = self.validator.validate_citations(
            report,
            self.sources,
            strict=False
        )

        assert not valid
        assert len(issues) > 0
        assert "phantom citations" in issues[0].lower()
        assert "5" in issues[0]
        assert "10" in issues[0]

    def test_validate_citations_strict_mode(self):
        """Test that strict mode raises CitationError."""
        report = """
        According to research [5], AI is important.
        """

        with pytest.raises(CitationError) as exc_info:
            self.validator.validate_citations(
                report,
                self.sources,
                strict=True
            )

        assert "phantom citations" in str(exc_info.value).lower()
        assert "5" in str(exc_info.value)

    def test_validate_citations_unused_sources(self):
        """Test detection of unused sources when < 50% are cited."""
        # Create a larger set of sources where < 50% are cited
        # This triggers the unused source warning
        many_sources = self.sources + [
            SearchResult(
                query="test",
                url="https://example.com/4",
                title="Source 4",
                snippet="snippet",
                content="content"
            ),
            SearchResult(
                query="test",
                url="https://example.com/5",
                title="Source 5",
                snippet="snippet",
                content="content"
            ),
        ]  # 5 sources total

        report = """
        According to McKinsey [1], AI will transform work.
        Brookings [2] confirms.
        """
        # Only uses [1] and [2] out of 5 sources = 40% cited < 50%

        valid, issues = self.validator.validate_citations(
            report,
            many_sources,
            strict=False
        )

        # Should warn about unused sources
        assert len(issues) > 0
        assert any("unused" in issue.lower() or "not cited" in issue.lower() for issue in issues)

    def test_sanitize_output_validate_section_quality(self):
        """Test removal of validate_section_quality calls."""
        report = """
        This is a research report.

        validate_section_quality(
            "Some long text here...",
            min_words=200
        )

        More content here.
        """

        cleaned = self.validator.sanitize_output(report)

        assert "validate_section_quality" not in cleaned
        assert "This is a research report" in cleaned
        assert "More content here" in cleaned

    def test_sanitize_output_debug_comments(self):
        """Test removal of debug comments."""
        report = """
        Research shows AI impact.
        # DEBUG: This should be removed
        More research content.
        """

        cleaned = self.validator.sanitize_output(report)

        assert "# DEBUG:" not in cleaned
        assert "Research shows AI impact" in cleaned

    def test_sanitize_output_print_statements(self):
        """Test removal of print statements."""
        report = """
        Analysis complete.
        print("Debug output")
        Final conclusions.
        """

        cleaned = self.validator.sanitize_output(report)

        assert "print(" not in cleaned
        assert "Analysis complete" in cleaned
        assert "Final conclusions" in cleaned

    def test_sanitize_output_code_blocks(self):
        """Test removal of stray Python code blocks."""
        report = """
        Research findings:

        ```python
        def debug_function():
            pass
        ```

        Conclusions follow.
        """

        cleaned = self.validator.sanitize_output(report)

        assert "```python" not in cleaned
        assert "def debug_function" not in cleaned
        assert "Research findings" in cleaned
        assert "Conclusions follow" in cleaned

    def test_sanitize_output_multiple_blank_lines(self):
        """Test cleanup of multiple blank lines."""
        report = "Line 1\n\n\n\n\nLine 2"

        cleaned = self.validator.sanitize_output(report)

        # Should reduce to at most 2 newlines (1 blank line)
        assert "\n\n\n" not in cleaned

    def test_validate_source_mentions_valid(self):
        """Test source mention validation with matching references."""
        report = """
        McKinsey's research shows AI impact on jobs.
        According to Brookings, hybrid jobs are emerging.
        """

        warnings = self.validator.validate_source_mentions(report, self.sources)

        # No warnings because McKinsey and Brookings are in sources
        assert len(warnings) == 0

    def test_validate_source_mentions_missing(self):
        """Test detection of mentioned sources without references."""
        report = """
        Deloitte's research shows job growth.
        BCG's modeling suggests 45% of jobs will change.
        Gartner forecasts 30% of jobs will involve AI.
        """

        warnings = self.validator.validate_source_mentions(report, self.sources)

        # Should warn about BCG and Gartner (at minimum)
        # Note: "Deloitte's 2024 analysis" might not match if pattern is specific
        assert len(warnings) >= 2
        assert any("bcg" in w.lower() for w in warnings)
        assert any("gartner" in w.lower() for w in warnings)

    def test_validate_source_mentions_partial(self):
        """Test mixed scenario with some valid, some missing sources."""
        report = """
        McKinsey's research shows AI impact.
        Deloitte's analysis confirms this.
        Brookings reports hybrid jobs emerging.
        """

        warnings = self.validator.validate_source_mentions(report, self.sources)

        # Should warn only about Deloitte
        assert len(warnings) == 1
        assert "deloitte" in warnings[0].lower()

    def test_validate_report_all_pass(self):
        """Test full report validation with all checks passing."""
        report = """
        AI Impact on Jobs

        According to McKinsey [1], AI will transform work.
        Brookings research [2] shows hybrid jobs emerging.
        LinkedIn's models [3] improve job matching.

        Conclusion

        The future of work is changing.
        """

        result = self.validator.validate_report(
            report,
            self.sources,
            auto_sanitize=True,
            strict_citations=False
        )

        # Validation should pass with all citations valid and no warnings
        assert result['citation_valid']
        assert len(result['citation_issues']) == 0
        assert len(result['source_warnings']) == 0

    def test_validate_report_with_artifacts(self):
        """Test report validation with debug artifacts."""
        report = """
        Research Report

        According to McKinsey [1], AI transforms work.

        validate_section_quality(
            "Some text",
            min_words=100
        )

        Brookings [2] and LinkedIn [3] confirm this.
        """

        result = self.validator.validate_report(
            report,
            self.sources,
            auto_sanitize=True,
            strict_citations=False
        )

        assert result['artifacts_removed']
        assert "validate_section_quality" not in result['cleaned_report']
        # All citations should be valid now
        assert result['citation_valid']

    def test_validate_report_with_phantom_citations(self):
        """Test report validation with phantom citations."""
        report = """
        Research shows [1] that AI is important.
        Other studies [5] and [10] confirm this.
        """

        result = self.validator.validate_report(
            report,
            self.sources,
            auto_sanitize=True,
            strict_citations=False
        )

        assert not result['valid']
        assert not result['citation_valid']
        assert len(result['citation_issues']) > 0
        assert "5" in result['citation_issues'][0]

    def test_validate_report_with_source_warnings(self):
        """Test report validation with missing source mentions."""
        report = """
        McKinsey [1] shows AI impact.
        Deloitte's analysis reveals job trends.
        Brookings [2] confirms hybrid jobs.
        """

        result = self.validator.validate_report(
            report,
            self.sources,
            auto_sanitize=True,
            strict_citations=False
        )

        assert len(result['source_warnings']) > 0
        assert any("deloitte" in w.lower() for w in result['source_warnings'])

    def test_fix_phantom_citations(self):
        """Test automatic fixing of phantom citations."""
        report = """
        Research [1] shows AI impact.
        Studies [5] and [10] confirm this trend.
        More findings [2] are available.
        """

        fixed = self.validator.fix_phantom_citations(report, self.sources)

        # Should remove [5] and [10]
        assert "[5]" not in fixed
        assert "[10]" not in fixed
        # Should keep [1] and [2]
        assert "[1]" in fixed
        assert "[2]" in fixed

    def test_fix_phantom_citations_no_change(self):
        """Test fixing when no phantom citations exist."""
        report = """
        Research [1] shows impact.
        Studies [2] confirm.
        """

        fixed = self.validator.fix_phantom_citations(report, self.sources)

        # Should be unchanged
        assert fixed == report

    def test_convenience_functions(self):
        """Test convenience wrapper functions."""
        from src.utils.report_validator import (
            validate_report,
            sanitize_report,
            check_citations
        )

        report = """
        McKinsey [1] shows AI impact.

        validate_section_quality("text", min_words=50)

        Brookings [2] and LinkedIn [3] confirm.
        """

        # Test validate_report
        result = validate_report(report, self.sources)
        assert 'valid' in result
        assert 'cleaned_report' in result

        # Test sanitize_report
        cleaned = sanitize_report(report)
        assert "validate_section_quality" not in cleaned

        # Test check_citations - all sources cited
        valid = check_citations("Research [1], [2], and [3]", self.sources)
        assert valid

        invalid = check_citations("Research [1] and [10]", self.sources)
        assert not invalid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
