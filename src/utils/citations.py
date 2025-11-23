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

        Args:
            report_content: The report text to update
            style: Citation style to use
            search_results: Search results with metadata
            credibility_scores: Credibility scores with recency information

        Returns:
            Updated report with formatted citations
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

        # Format new references section with date information
        new_references = f"## References\n\n{self.format_references_section(urls, style, search_results, credibility_scores)}"

        # Replace references section
        updated_report = re.sub(
            r'## References\n\n.*?(?=\n##|\Z)',
            new_references,
            report_content,
            flags=re.DOTALL
        )

        return updated_report

