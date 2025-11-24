"""Citation formatting utilities for different citation styles."""

from typing import List, Dict
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class CitationFormatter:
    """Format citations in different academic styles."""
    
    def __init__(self):
        self.styles = ['apa', 'mla', 'chicago', 'ieee']
    
    def format_apa(self, url: str, title: str = "", author: str = "", date: str = "") -> str:
        """Format citation in APA style."""
        if author and date:
            return f"{author} ({date}). {title}. Retrieved from {url}"
        elif date and title:
            return f"{title}. ({date}). Retrieved from {url}"
        elif date:
            return f"({date}). Retrieved from {url}"
        elif title:
            return f"{title}. (n.d.). Retrieved from {url}"
        else:
            return f"Retrieved from {url}"
    
    def format_mla(self, url: str, title: str = "", author: str = "", date: str = "") -> str:
        """Format citation in MLA style."""
        parts = []
        if author:
            parts.append(author)
        if title:
            parts.append(f'"{title}"')
        if date:
            parts.append(date)
        parts.append(f"Web. {datetime.now().strftime('%d %b. %Y')}")
        parts.append(f"<{url}>")
        return ". ".join(parts)
    
    def format_chicago(self, url: str, title: str = "", author: str = "", date: str = "") -> str:
        """Format citation in Chicago style."""
        if author:
            return f"{author}. \"{title}.\" Accessed {datetime.now().strftime('%B %d, %Y')}. {url}."
        else:
            return f"\"{title}.\" Accessed {datetime.now().strftime('%B %d, %Y')}. {url}."
    
    def format_ieee(self, url: str, title: str = "", author: str = "", date: str = "") -> str:
        """Format citation in IEEE style."""
        if author:
            return f"{author}, \"{title},\" {url}, accessed {datetime.now().strftime('%B %d, %Y')}."
        else:
            return f"\"{title},\" {url}, accessed {datetime.now().strftime('%B %d, %Y')}."
    
    def format_references_section(
        self,
        urls: List[str],
        style: str = 'apa',
        search_results: List = None,
        credibility_scores: List[Dict] = None
    ) -> str:
        """Format a references section in the specified style.

        Args:
            urls: List of URLs to cite
            style: Citation style ('apa', 'mla', 'chicago', 'ieee')
            search_results: Optional search results to extract metadata
            credibility_scores: Optional credibility scores with recency info

        Returns:
            Formatted references section
        """
        style = style.lower()
        if style not in self.styles:
            style = 'apa'
            logger.warning(f"Unknown style {style}, defaulting to APA")

        # Create URL to metadata mapping
        url_metadata = {}
        if search_results:
            for i, result in enumerate(search_results):
                if hasattr(result, 'url') and result.url:
                    metadata = {
                        'title': getattr(result, 'title', ''),
                        'snippet': getattr(result, 'snippet', '')
                    }

                    # Extract date from credibility scores if available
                    if credibility_scores and i < len(credibility_scores):
                        cred_score = credibility_scores[i]
                        if 'recency' in cred_score:
                            recency_info = cred_score['recency']
                            if 'date' in recency_info:
                                metadata['date'] = recency_info['date']

                    url_metadata[result.url] = metadata

        references = []
        for i, url in enumerate(urls, 1):
            metadata = url_metadata.get(url, {})
            title = metadata.get('title', '')
            date = metadata.get('date', '')

            if style == 'apa':
                citation = self.format_apa(url, title, date=date)
            elif style == 'mla':
                citation = self.format_mla(url, title, date=date)
            elif style == 'chicago':
                citation = self.format_chicago(url, title, date=date)
            elif style == 'ieee':
                citation = self.format_ieee(url, title, date=date)
            else:
                citation = url

            references.append(f"{i}. {citation}")

        return "\n".join(references)
    
    def update_report_citations(
        self,
        report_content: str,
        style: str = 'apa',
        search_results: List = None,
        credibility_scores: List[Dict] = None
    ) -> str:
        """Update citations in a report to use specified style with dates.

        This updates the references section but keeps inline citations as [1], [2], etc.
        Also removes unused references that aren't actually cited in the text.

        Args:
            report_content: The report text to update
            style: Citation style to use
            search_results: Search results with metadata
            credibility_scores: Credibility scores with recency information

        Returns:
            Updated report with formatted citations and cleaned references
        """
        # Extract URLs from references section
        references_match = re.search(
            r'## References\n\n(.*?)(?=\n##|\Z)',
            report_content,
            re.DOTALL
        )

        if not references_match:
            return report_content

        # Extract URLs from existing references
        url_pattern = r'https?://[^\s\)]+'
        existing_refs = references_match.group(1)
        urls = re.findall(url_pattern, existing_refs)

        if not urls:
            return report_content

        # Find all cited numbers in the report text (excluding References section)
        text_before_refs = report_content[:references_match.start()]
        cited_numbers = set(re.findall(r'\[(\d+)\]', text_before_refs))

        # Filter URLs to only include those that are actually cited
        filtered_urls = []
        filtered_search_results = []
        filtered_cred_scores = []

        for i, url in enumerate(urls):
            citation_num = str(i + 1)
            if citation_num in cited_numbers:
                filtered_urls.append(url)
                if search_results and i < len(search_results):
                    filtered_search_results.append(search_results[i])
                if credibility_scores and i < len(credibility_scores):
                    filtered_cred_scores.append(credibility_scores[i])

        if not filtered_urls:
            # If filtering removed all URLs, keep originals (safety fallback)
            logger.warning("Filtering removed all references - keeping original list")
            filtered_urls = urls
            filtered_search_results = search_results if search_results else []
            filtered_cred_scores = credibility_scores if credibility_scores else []
        else:
            logger.info(f"Cleaned references: {len(urls)} -> {len(filtered_urls)} (removed {len(urls) - len(filtered_urls)} unused)")

        # Format new references section with date information
        new_references = f"## References\n\n{self.format_references_section(filtered_urls, style, filtered_search_results or None, filtered_cred_scores or None)}"

        # Replace references section
        updated_report = re.sub(
            r'## References\n\n.*?(?=\n##|\Z)',
            new_references,
            report_content,
            flags=re.DOTALL
        )

        return updated_report

    def verify_citation_relevance(
        self,
        report_content: str,
        search_results: List = None
    ) -> List[Dict[str, str]]:
        """Verify that citations are relevant to the claims they support.

        Detects potential mismatches like citing a 6G networks paper for layoff statistics.

        Args:
            report_content: The report text to check
            search_results: Search results with metadata

        Returns:
            List of warnings about suspicious citations
        """
        if not search_results:
            return []

        warnings = []

        # Extract sentences with citations
        # Pattern: sentence ending with citation like [1] or [1,2] or [1][2]
        citation_pattern = r'([^.!?]+[\[,\s]*(?:\[\d+\])+[.!?])'
        cited_sentences = re.findall(citation_pattern, report_content)

        for sentence in cited_sentences:
            # Extract citation numbers from this sentence
            citation_nums = re.findall(r'\[(\d+)\]', sentence)

            if not citation_nums:
                continue

            # Remove citations from sentence to get the claim
            claim = re.sub(r'\[\d+\]', '', sentence).strip()

            # Check each citation
            for cite_num in citation_nums:
                idx = int(cite_num) - 1  # Convert to 0-indexed

                if idx >= len(search_results):
                    continue

                result = search_results[idx]
                source_text = f"{getattr(result, 'title', '')} {getattr(result, 'snippet', '')}".lower()

                # Define keyword categories and their expected source keywords
                mismatch_patterns = [
                    # If claim is about layoffs/jobs, source should mention employment terms
                    {
                        'claim_keywords': ['layoff', 'laid off', 'job loss', 'workforce reduction', 'firing', 'downsizing'],
                        'required_source_keywords': ['job', 'employ', 'layoff', 'workforce', 'worker', 'hiring', 'labor', 'labour'],
                        'warning_prefix': 'Layoff/employment claim'
                    },
                    # If claim mentions specific companies, source should mention them
                    {
                        'claim_keywords': ['google', 'amazon', 'microsoft', 'meta', 'apple'],
                        'required_source_keywords': ['tech', 'company', 'corporation', 'google', 'amazon', 'microsoft', 'meta', 'apple'],
                        'warning_prefix': 'Company-specific claim'
                    },
                    # If claim is about statistics/data, source should contain numbers or research
                    {
                        'claim_keywords': ['percent', '%', 'million', 'thousand', 'billion', 'statistics', 'data shows'],
                        'required_source_keywords': ['percent', '%', 'data', 'statistics', 'study', 'survey', 'research', 'report', 'analysis'],
                        'warning_prefix': 'Statistical claim'
                    }
                ]

                claim_lower = claim.lower()

                for pattern in mismatch_patterns:
                    # Check if claim contains any of the claim keywords
                    has_claim_keyword = any(kw in claim_lower for kw in pattern['claim_keywords'])

                    if has_claim_keyword:
                        # Check if source contains any of the required keywords
                        has_source_keyword = any(kw in source_text for kw in pattern['required_source_keywords'])

                        if not has_source_keyword:
                            source_title = getattr(result, 'title', 'Unknown')[:80]
                            warnings.append({
                                'type': 'citation_mismatch',
                                'citation': cite_num,
                                'claim': claim[:150],
                                'source_title': source_title,
                                'warning': f"{pattern['warning_prefix']} may not match source"
                            })
                            logger.warning(
                                f"Potential citation mismatch: [{cite_num}] '{source_title}' "
                                f"cited for: '{claim[:100]}...'"
                            )
                            break  # Only warn once per citation

        return warnings

