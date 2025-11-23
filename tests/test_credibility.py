"""Tests for credibility scoring system."""

import pytest
from src.utils.credibility import CredibilityScorer
from src.state import SearchResult


class TestCredibilityScorer:
    """Test the CredibilityScorer class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.scorer = CredibilityScorer()

    def test_consulting_firm_high_score(self):
        """Test that consulting firms get high credibility scores."""
        urls = [
            "https://www.mckinsey.com/insights/future-of-work",
            "https://www.bcg.com/publications/2024/ai-transformation",
            "https://www.accenture.com/insights/technology-trends",
            "https://www.deloitte.com/insights/future-workforce",
            "https://www.bain.com/insights/automation-impact"
        ]

        for url in urls:
            result = self.scorer.score_url(url)
            assert result['score'] >= 85, f"Expected high score for {url}, got {result['score']}"
            assert result['level'] == 'high'
            assert result['source_type'] == 'consulting'

    def test_academic_repository_high_score(self):
        """Test that academic repositories get high credibility scores."""
        urls = [
            "https://arxiv.org/abs/2024.12345",
            "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=123456",
            "https://biorxiv.org/content/10.1101/2024.01.01.123456v1"
        ]

        for url in urls:
            result = self.scorer.score_url(url)
            assert result['score'] >= 85, f"Expected high score for {url}, got {result['score']}"
            assert result['level'] == 'high'
            assert result['source_type'] == 'academic'

    def test_professional_community_medium_score(self):
        """Test that professional communities get medium scores."""
        urls = [
            "https://news.ycombinator.com/item?id=123456",
            "https://www.reddit.com/r/MachineLearning/comments/abc123/discussion"
        ]

        for url in urls:
            result = self.scorer.score_url(url)
            # Should be at least medium level (40+)
            assert result['score'] >= 40, f"Expected medium score for {url}, got {result['score']}"
            assert result['level'] in ['medium', 'high']

    def test_government_domain_high_score(self):
        """Test that .gov domains get high scores."""
        url = "https://www.bls.gov/news.release/pdf/empsit.pdf"
        result = self.scorer.score_url(url)

        assert result['score'] >= 75
        assert result['level'] == 'high'
        assert any('.gov' in f for f in result['factors'])

    def test_edu_domain_high_score(self):
        """Test that .edu domains get high scores."""
        url = "https://ai.stanford.edu/research/future-of-work"
        result = self.scorer.score_url(url)

        assert result['score'] >= 75
        assert result['level'] == 'high'
        assert any('.edu' in f for f in result['factors'])

    def test_https_bonus(self):
        """Test that HTTPS URLs get a bonus."""
        https_url = "https://example.com/article"
        http_url = "http://example.com/article"

        https_result = self.scorer.score_url(https_url)
        http_result = self.scorer.score_url(http_url)

        assert https_result['score'] > http_result['score']
        assert 'HTTPS enabled' in https_result['factors']
        assert 'No HTTPS' in http_result['factors']

    def test_research_path_bonus(self):
        """Test that research/publications paths get bonuses."""
        paths = [
            "https://example.com/research/ai-impact.html",
            "https://example.com/publications/future-work.pdf",
            "https://example.com/papers/automation-study.html"
        ]

        for url in paths:
            result = self.scorer.score_url(url)
            assert any('Research' in f or 'research' in f for f in result['factors'])

    def test_insights_reports_bonus(self):
        """Test that insights/reports paths get bonuses."""
        urls = [
            "https://example.com/insights/ai-trends",
            "https://example.com/reports/2024-outlook"
        ]

        for url in urls:
            result = self.scorer.score_url(url)
            assert any('insights' in f.lower() or 'reports' in f.lower() for f in result['factors'])

    def test_suspicious_domain_penalty(self):
        """Test that suspicious domains get penalized."""
        suspicious_urls = [
            "https://example.xyz/article",
            "https://bit.ly/shortened",
            "https://myblog.blogspot.com/post"
        ]

        for url in suspicious_urls:
            result = self.scorer.score_url(url)
            assert result['score'] < 50

    def test_invalid_url_returns_zero(self):
        """Test that invalid URLs return zero score."""
        result = self.scorer.score_url("")
        assert result['score'] == 0
        assert result['level'] == 'low'

        result = self.scorer.score_url(None)
        assert result['score'] == 0

    def test_score_search_results(self):
        """Test scoring a list of search results."""
        results = [
            SearchResult(
                query="test",
                title="McKinsey Report",
                url="https://www.mckinsey.com/insights/test",
                snippet="Test snippet"
            ),
            SearchResult(
                query="test",
                title="Blog Post",
                url="https://myblog.blogspot.com/test",
                snippet="Test snippet"
            ),
            SearchResult(
                query="test",
                title="arXiv Paper",
                url="https://arxiv.org/abs/2024.12345",
                snippet="Test snippet"
            )
        ]

        scored = self.scorer.score_search_results(results)

        # Should be sorted by score (highest first)
        assert len(scored) == 3
        assert scored[0]['credibility']['score'] >= scored[1]['credibility']['score']
        assert scored[1]['credibility']['score'] >= scored[2]['credibility']['score']

    def test_filter_by_credibility(self):
        """Test filtering results by minimum credibility score."""
        results = [
            SearchResult(
                query="test",
                title="High Credibility",
                url="https://www.mckinsey.com/insights/test",
                snippet="Test"
            ),
            SearchResult(
                query="test",
                title="Medium Credibility",
                url="https://example.com/test",
                snippet="Test"
            ),
            SearchResult(
                query="test",
                title="Low Credibility",
                url="https://spam.xyz/test",
                snippet="Test"
            )
        ]

        # Filter with min_score=70 should keep only high-credibility sources
        filtered = self.scorer.filter_by_credibility(results, min_score=70)

        assert len(filtered) < len(results)
        # McKinsey should pass, spam should not
        urls = [r.url for r in filtered]
        assert "https://www.mckinsey.com/insights/test" in urls
        assert "https://spam.xyz/test" not in urls

    def test_arxiv_pdf_bonus(self):
        """Test that arXiv PDF links get bonus points."""
        pdf_url = "https://arxiv.org/pdf/2024.12345.pdf"
        abs_url = "https://arxiv.org/abs/2024.12345"

        pdf_result = self.scorer.score_url(pdf_url)
        abs_result = self.scorer.score_url(abs_url)

        # Both should be high, but PDF might have slight bonus
        assert pdf_result['score'] >= abs_result['score']
        assert 'Direct PDF link' in pdf_result['factors']

    def test_reddit_quality_subreddit_bonus(self):
        """Test that quality subreddits get bonus points."""
        quality_url = "https://www.reddit.com/r/MachineLearning/comments/test"
        random_url = "https://www.reddit.com/r/random/comments/test"

        quality_result = self.scorer.score_url(quality_url)
        random_result = self.scorer.score_url(random_url)

        # Quality subreddit should score higher
        assert quality_result['score'] >= random_result['score']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
