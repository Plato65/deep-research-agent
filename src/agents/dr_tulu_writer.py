"""
DR Tulu Report Writer

Uses DR Tulu-8B for research report generation with 88.6% citation precision.
Converts DR Tulu's <cite id="SOURCE_N"> format to standard [N] format.
"""

import re
import logging
import asyncio
import time
from typing import List, Dict, Tuple
from openai import OpenAI, AsyncOpenAI

from src.state import ResearchState, SearchResult
from src.config import config
from src.utils.tokens import estimate_tokens

logger = logging.getLogger(__name__)


class DRTuluReportWriter:
    """Report writer using DR Tulu-8B for improved citation accuracy."""

    def __init__(self, endpoint: str = "http://localhost:30001/v1", citation_style: str = None):
        """Initialize DR Tulu writer.

        Args:
            endpoint: VLLM server endpoint (default: http://localhost:30001/v1)
            citation_style: Citation style (not used - DR Tulu handles citations)
        """
        self.endpoint = endpoint
        self.citation_style = citation_style or config.citation_style
        self.max_retries = config.max_retries

        # Use async OpenAI client for VLLM
        self.client = AsyncOpenAI(
            base_url=endpoint,
            api_key="dummy"  # VLLM doesn't require real API key
        )

        logger.info(f"DRTuluReportWriter initialized (endpoint: {endpoint})")

    def _format_sources_with_ids(self, search_results: List[SearchResult]) -> str:
        """Format sources with explicit SOURCE_N IDs for DR Tulu.

        Args:
            search_results: List of search results

        Returns:
            Formatted sources text with IDs
        """
        sources_text = ""
        for i, result in enumerate(search_results[:20], start=1):  # Top 20 sources
            source_id = f"SOURCE_{i}"
            sources_text += f"\n[{source_id}] {result.title}\n"
            sources_text += f"URL: {result.url}\n"
            if result.snippet:
                sources_text += f"Snippet: {result.snippet}\n"
            if result.content:
                # Limit content to avoid context overflow
                content_preview = result.content[:500]
                sources_text += f"Content: {content_preview}...\n"
            sources_text += "\n"

        return sources_text

    def _create_dr_tulu_prompt(
        self,
        topic: str,
        section_title: str,
        findings: List[str],
        sources: List[SearchResult]
    ) -> str:
        """Create DR Tulu-formatted prompt.

        DR Tulu uses:
        - <think> tags for reasoning
        - <cite id="SOURCE_N">claim</cite> for citations
        - Structured output in <answer> tags

        Args:
            topic: Research topic
            section_title: Section to write
            findings: Key findings
            sources: Search results

        Returns:
            Formatted prompt for DR Tulu
        """
        sources_text = self._format_sources_with_ids(sources)
        findings_text = "\n".join([f"- {finding}" for finding in findings[:15]])

        prompt = f"""<think>
I need to write a comprehensive research section on "{section_title}" for the topic: {topic}

Key findings to incorporate:
{findings_text}

Available sources:
{sources_text}

I should:
1. Use ONLY information from the provided sources
2. Cite claims using <cite id="SOURCE_N">claim text</cite> format
3. Ensure every factual claim has a citation
4. Write in clear, academic language
5. Aim for 300-500 words minimum
6. Include specific data and statistics when available
</think>

<answer>
## {section_title}

"""

        return prompt

    def _convert_dr_tulu_citations(self, text: str) -> str:
        """Convert DR Tulu citations to standard format.

        Converts:
            <cite id="SOURCE_5">claim</cite> → claim [5]

        Args:
            text: Report text with DR Tulu citations

        Returns:
            Text with standard [N] citations
        """
        # Pattern: <cite id="SOURCE_N">claim text</cite>
        pattern = r'<cite id="SOURCE_(\d+)">(.*?)</cite>'

        def replace_citation(match):
            source_num = match.group(1)
            claim_text = match.group(2)
            return f"{claim_text} [{source_num}]"

        converted = re.sub(pattern, replace_citation, text, flags=re.DOTALL)

        # Remove any remaining XML-like tags
        converted = re.sub(r'</?think>', '', converted)
        converted = re.sub(r'</?answer>', '', converted)
        converted = re.sub(r'</?call_tool[^>]*>', '', converted)

        return converted.strip()

    async def _write_section_with_dr_tulu(
        self,
        topic: str,
        section_title: str,
        findings: List[str],
        sources: List[SearchResult]
    ) -> Tuple[str, Dict]:
        """Write a single section using DR Tulu.

        Args:
            topic: Research topic
            section_title: Section to write
            findings: Key findings
            sources: Search results

        Returns:
            Tuple of (section_text, token_usage)
        """
        logger.info(f"Writing section with DR Tulu: {section_title}")

        prompt = self._create_dr_tulu_prompt(topic, section_title, findings, sources)

        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model="rl-research/DR-Tulu-8B",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research writer. Write comprehensive, well-cited research sections using the provided sources."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4096,
                temperature=0.7,
                stop=["</answer>"]
            )

            duration = time.time() - start_time

            # Extract section text
            section_text = response.choices[0].message.content

            # Convert DR Tulu citations to standard format
            section_text = self._convert_dr_tulu_citations(section_text)

            # Token usage
            input_tokens = response.usage.prompt_tokens if response.usage else estimate_tokens(prompt)
            output_tokens = response.usage.completion_tokens if response.usage else estimate_tokens(section_text)

            token_info = {
                'agent': 'DRTuluReportWriter',
                'operation': f'write_section_{section_title}',
                'model': 'rl-research/DR-Tulu-8B',
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'duration': round(duration, 2)
            }

            logger.info(f"DR Tulu section complete: {len(section_text)} chars, {output_tokens} tokens")

            return section_text, token_info

        except Exception as e:
            logger.error(f"DR Tulu section writing failed: {str(e)}")
            raise

    async def write_report(self, state: ResearchState) -> dict:
        """Write the final research report using DR Tulu.

        Compatible with existing ReportWriter interface for easy integration.

        Args:
            state: Current research state

        Returns:
            Dict with report data that LangGraph will merge into state
        """
        logger.info("Writing final report with DR Tulu")

        if not state.plan or not state.key_findings:
            return {"error": "Insufficient data for report generation"}

        # Track LLM calls for report generation
        report_llm_calls = 0
        report_input_tokens = 0
        report_output_tokens = 0
        report_call_details = []

        for attempt in range(self.max_retries):
            try:
                # Generate each section with DR Tulu
                report_sections = []

                for section_title in state.plan.report_outline:
                    section, section_tokens = await self._write_section_with_dr_tulu(
                        state.research_topic,
                        section_title,
                        state.key_findings,
                        state.search_results[:20]  # Top 20 sources
                    )

                    if section:
                        report_sections.append(section)
                        report_llm_calls += 1
                        report_input_tokens += section_tokens['input_tokens']
                        report_output_tokens += section_tokens['output_tokens']
                        report_call_details.append(section_tokens)

                # Validate minimum quality
                if not report_sections:
                    raise ValueError("No report sections generated")

                # Compile final report
                final_report = self._compile_report(state, report_sections)

                # Add credibility information if available
                if state.credibility_scores:
                    high_cred_sources = [
                        i+1 for i, score in enumerate(state.credibility_scores)
                        if score.get('level') == 'high'
                    ]
                    if high_cred_sources:
                        final_report += f"\n\n---\n\n**Note:** {len(high_cred_sources)} high-credibility sources were prioritized in this research."

                # Validate report length
                if len(final_report) < 500:
                    raise ValueError("Report too short - insufficient content")

                logger.info(f"DR Tulu report generation complete: {len(final_report)} chars")

                # Return dict updates - LangGraph merges into state
                return {
                    "report_sections": report_sections,
                    "final_report": final_report,
                    "current_stage": "complete",
                    "iterations": state.iterations + 1,
                    "llm_calls": state.llm_calls + report_llm_calls,
                    "total_input_tokens": state.total_input_tokens + report_input_tokens,
                    "total_output_tokens": state.total_output_tokens + report_output_tokens,
                    "llm_call_details": state.llm_call_details + report_call_details
                }

            except Exception as e:
                logger.warning(f"DR Tulu report attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"DR Tulu report generation failed after {self.max_retries} attempts")
                    return {
                        "error": f"DR Tulu report writing failed: {str(e)}",
                        "iterations": state.iterations + 1
                    }
                else:
                    await asyncio.sleep(2 ** attempt)

        # Fallback if all retries exhausted
        return {
            "error": "DR Tulu report generation failed: Maximum retries exceeded",
            "iterations": state.iterations + 1
        }

    def _compile_report(self, state: ResearchState, sections: List[str]) -> str:
        """Compile report sections into final document.

        Args:
            state: Research state
            sections: List of section texts

        Returns:
            Complete report text
        """
        report = f"# {state.research_topic}\n\n"

        # Add sections
        for section in sections:
            report += section + "\n\n"

        # Add References section
        report += "## References\n\n"

        if state.search_results:
            for i, result in enumerate(state.search_results[:20], start=1):
                title = result.title or "Untitled"
                url = result.url

                # Get date from credibility scores if available
                date = ""
                if state.credibility_scores and i-1 < len(state.credibility_scores):
                    cred_info = state.credibility_scores[i-1]
                    if 'recency' in cred_info and 'date' in cred_info['recency']:
                        date = f" ({cred_info['recency']['date']})"

                report += f"[{i}] {title}{date}. Retrieved from {url}\n\n"

        return report
