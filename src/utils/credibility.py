"""Source credibility scoring based on domain authority and other factors."""

import re
from typing import List, Dict, Any
from urllib.parse import urlparse
import logging

from src.utils.recency import RecencyScorer

logger = logging.getLogger(__name__)


class CredibilityScorer:
    """Score sources based on domain authority and other credibility factors."""

    def __init__(self, enable_recency_scoring: bool = True):
        """Initialize the credibility scorer.

        Args:
            enable_recency_scoring: Whether to include recency in scoring (default: True)
        """
        self.enable_recency_scoring = enable_recency_scoring
        self.recency_scorer = RecencyScorer() if enable_recency_scoring else None

    # Trusted domains
    TRUSTED_DOMAINS = {
        # Academic institutions (global)
        '.edu', '.ac.uk', '.ac.in', '.edu.in', '.edu.au', '.ac.jp',

        # Government (global)
        '.gov', '.gov.uk', '.gov.au', '.gov.ca', '.gov.in', '.europa.eu',

        # International news organizations
        'bbc.com', 'bbc.co.uk', 'reuters.com', 'ap.org', 'npr.org',
        'theguardian.com', 'nytimes.com', 'washingtonpost.com', 'wsj.com',
        'ft.com', 'economist.com', 'bloomberg.com', 'cnbc.com',
        'cnn.com', 'aljazeera.com', 'france24.com', 'dw.com',

        # Indian news organizations
        'thehindu.com', 'indianexpress.com', 'timesofindia.com', 'indiatimes.com',
        'economictimes.com', 'financialexpress.com', 'livemint.com',
        'business-standard.com', 'moneycontrol.com', 'businessline.in',
        'businesstoday.in', 'businessinsider.in',

        # Academic & Research platforms
        'arxiv.org', 'scholar.google.com', 'researchgate.net', 'semanticscholar.org',
        'pubmed.ncbi.nlm.nih.gov', 'ncbi.nlm.nih.gov', 'nih.gov', 'nature.com',
        'sciencedirect.com', 'springer.com', 'wiley.com', 'ieee.org',
        'jstor.org', 'plos.org', 'sciencemag.org', 'cell.com',
        'papers.ssrn.com', 'ssrn.com',  # SSRN papers

        # Medical & Health organizations
        'who.int', 'cdc.gov', 'mayoclinic.org', 'nih.gov', 'webmd.com',

        # International organizations
        'un.org', 'worldbank.org', 'imf.org', 'wto.org', 'oecd.org',

        # Tech & Science publications
        'nature.com', 'scientificamerican.com', 'newscientist.com',
        'technologyreview.com', 'spectrum.ieee.org', 'arstechnica.com',
        'wired.com', 'techcrunch.com', 'theverge.com',

        # Wikipedia & educational resources
        'wikipedia.org', 'britannica.com', 'khanacademy.org',

        # Legal & policy
        'supremecourt.gov', 'congress.gov', 'loc.gov',

        # Statistics & data
        'census.gov', 'bls.gov', 'data.gov', 'worldbank.org',
        'statista.com', 'pewresearch.org', 'gallup.com'
    }

    # Consulting firms (HIGH credibility for business/strategy content)
    CONSULTING_FIRMS = {
        'mckinsey.com': 'McKinsey & Company',
        'bcg.com': 'Boston Consulting Group',
        'accenture.com': 'Accenture',
        'deloitte.com': 'Deloitte',
        'bain.com': 'Bain & Company',
        'pwc.com': 'PwC',
        'ey.com': 'Ernst & Young',
        'kpmg.com': 'KPMG',
        'oliverwyman.com': 'Oliver Wyman',
        'atkearney.com': 'A.T. Kearney',
        'mckinsey.com/mgi': 'McKinsey Global Institute'
    }

    # Academic preprint/paper servers (HIGH credibility)
    ACADEMIC_REPOSITORIES = {
        'arxiv.org': 'arXiv',
        'papers.ssrn.com': 'SSRN',
        'biorxiv.org': 'bioRxiv',
        'medrxiv.org': 'medRxiv',
        'osf.io/preprints': 'OSF Preprints'
    }

    # Tech/professional communities (MEDIUM-HIGH credibility)
    PROFESSIONAL_COMMUNITIES = {
        'news.ycombinator.com': 'Hacker News',
        'reddit.com/r/machinelearning': 'Reddit ML',
        'reddit.com/r/datascience': 'Reddit Data Science',
        'reddit.com/r/artificial': 'Reddit AI',
        'reddit.com/r/science': 'Reddit Science'
    }
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        r'\.(xyz|tk|ml|ga|cf|gq)$',  # Suspicious TLDs
        r'bit\.ly|tinyurl|t\.co',  # URL shorteners
        r'blogspot|wordpress\.com',  # Personal blogs (lower credibility)
    ]
    
    def score_url(self, url: str, title: str = "", snippet: str = "") -> Dict[str, Any]:
        """Score a URL's credibility including recency.

        Args:
            url: URL to score
            title: Title of the source (optional, for recency detection)
            snippet: Snippet/description (optional, for recency detection)

        Returns:
            Dict with 'score' (0-100), 'factors', 'level' (low/medium/high), 'source_type', 'recency'
        """
        if not url:
            return {'score': 0, 'factors': ['No URL'], 'level': 'low', 'source_type': 'unknown'}

        score = 50  # Base score
        factors = []
        source_type = 'general'
        recency_info = None

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            full_path = domain + parsed.path

            # Check for consulting firms (HIGHEST priority for business content)
            for firm_domain, firm_name in self.CONSULTING_FIRMS.items():
                if firm_domain in domain:
                    score += 35
                    factors.append(f'Consulting firm: {firm_name}')
                    source_type = 'consulting'
                    break

            # Check for academic repositories
            if source_type == 'general':
                for repo_domain, repo_name in self.ACADEMIC_REPOSITORIES.items():
                    if repo_domain in domain:
                        score += 35
                        factors.append(f'Academic repository: {repo_name}')
                        source_type = 'academic'
                        break

            # Check for professional communities
            if source_type == 'general':
                for comm_domain, comm_name in self.PROFESSIONAL_COMMUNITIES.items():
                    if comm_domain in full_path:
                        score += 20
                        factors.append(f'Professional community: {comm_name}')
                        source_type = 'community'
                        break

            # Check for general trusted domains
            if source_type == 'general':
                for trusted in self.TRUSTED_DOMAINS:
                    if trusted in domain:
                        score += 30
                        factors.append(f'Trusted domain: {trusted}')
                        source_type = 'trusted'
                        break

            # Check for suspicious patterns
            is_suspicious = False
            for pattern in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, domain):
                    score -= 20
                    factors.append(f'Suspicious pattern detected')
                    is_suspicious = True
                    break

            # HTTPS bonus
            if parsed.scheme == 'https':
                score += 5
                factors.append('HTTPS enabled')
            else:
                score -= 10
                factors.append('No HTTPS')

            # Domain structure penalty
            if source_type == 'general' and not is_suspicious:
                if len(domain.split('.')) > 3:
                    score -= 5
                    factors.append('Complex domain structure')

            # Path-based bonuses
            path_lower = parsed.path.lower()

            if '/papers/' in path_lower or '/research/' in path_lower or '/publications/' in path_lower:
                score += 10
                factors.append('Research/publications path')

            if '/insights/' in path_lower or '/reports/' in path_lower:
                score += 8
                factors.append('Insights/reports section')

            if '/blog/' in path_lower and source_type != 'consulting':
                score -= 5  # Blogs generally less authoritative
                factors.append('Blog content (lower authority)')

            # Consulting-specific paths
            if source_type == 'consulting':
                if any(x in path_lower for x in ['/insights/', '/publications/', '/featured-insights/']):
                    score += 5
                    factors.append('Professional insights section')

            # Reddit-specific: Check for quality subreddits
            if 'reddit.com' in domain:
                quality_subreddits = ['science', 'machinelearning', 'datascience', 'artificial', 'technology']
                if any(f'/r/{sub}' in path_lower for sub in quality_subreddits):
                    score += 10
                    factors.append('Quality subreddit')
                    source_type = 'community'

            # arXiv-specific: Check for PDF vs abstract
            if 'arxiv.org' in domain:
                if '/pdf/' in path_lower:
                    score += 5
                    factors.append('Direct PDF link')

            # Recency scoring (add bonus for recent content)
            if self.enable_recency_scoring and self.recency_scorer:
                recency_info = self.recency_scorer.score_source_recency(url, title, snippet)
                recency_bonus = recency_info.get('score', 0)
                if recency_bonus > 0:
                    score += recency_bonus
                    factors.append(recency_info.get('factor', 'Recent content'))

            # Normalize score to 0-100
            score = max(0, min(100, score))

            # Determine level
            if score >= 70:
                level = 'high'
            elif score >= 40:
                level = 'medium'
            else:
                level = 'low'

            result = {
                'score': score,
                'factors': factors if factors else ['Standard domain'],
                'level': level,
                'domain': domain,
                'source_type': source_type
            }

            # Include recency information if available
            if recency_info:
                result['recency'] = recency_info

            return result

        except Exception as e:
            logger.warning(f"Error scoring URL {url}: {e}")
            return {
                'score': 30,
                'factors': ['Scoring error'],
                'level': 'low',
                'source_type': 'unknown'
            }
    
    def score_search_results(self, results: List) -> List[Dict]:
        """Score a list of search results including recency."""
        scored = []
        for result in results:
            # Extract URL, title, and snippet
            if hasattr(result, 'url'):
                url = result.url
                title = getattr(result, 'title', '')
                snippet = getattr(result, 'snippet', '')
            elif isinstance(result, dict):
                url = result.get('url', '')
                title = result.get('title', '')
                snippet = result.get('snippet', '')
            else:
                url = str(result)
                title = ''
                snippet = ''

            # Score with recency information
            credibility = self.score_url(url, title, snippet)
            scored.append({
                'result': result,
                'credibility': credibility
            })

        # Sort by credibility score (highest first)
        scored.sort(key=lambda x: x['credibility']['score'], reverse=True)
        return scored
    
    def filter_by_credibility(self, results: List, min_score: int = 40, max_age_days: int = 0) -> List:
        """Filter results by minimum credibility score and optional maximum age.

        Args:
            results: List of search results to filter
            min_score: Minimum credibility score (0-100)
            max_age_days: Maximum age in days (0 = no age filter)

        Returns:
            Filtered list of results
        """
        scored = self.score_search_results(results)
        filtered = []
        age_filtered_count = 0

        for item in scored:
            # Check credibility score
            if item['credibility']['score'] < min_score:
                continue

            # Check age if filtering is enabled
            if max_age_days > 0 and 'recency' in item['credibility']:
                recency_info = item['credibility']['recency']
                age_days = recency_info.get('age_days')

                # If we have age info and it's too old, skip it
                if age_days is not None and age_days > max_age_days:
                    age_filtered_count += 1
                    logger.debug(f"Filtered out source older than {max_age_days} days: {age_days} days old")
                    continue

            filtered.append(item['result'])

        logger.info(f"Filtered {len(results)} -> {len(filtered)} results "
                   f"(min_score={min_score}, age_filtered={age_filtered_count})")
        return filtered

