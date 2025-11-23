"""Parser for extracting search results from agent messages.

This module provides robust parsing of LangChain agent outputs,
replacing the brittle inline parsing previously in agents.py.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from src.state import SearchResult

logger = logging.getLogger(__name__)


class SearchResultParser:
    """Parses search results from LangChain agent message outputs."""

    @staticmethod
    def parse_agent_messages(messages: List[Any]) -> List[SearchResult]:
        """Parse search results from agent messages.

        Args:
            messages: List of messages from agent execution

        Returns:
            List of SearchResult objects
        """
        search_results = []

        try:
            for msg in messages:
                # Extract search results from tool responses
                if hasattr(msg, 'name') and msg.name == 'web_search':
                    results = SearchResultParser._parse_web_search_response(msg)
                    search_results.extend(results)

                # Extract content extraction results
                elif hasattr(msg, 'name') and msg.name == 'extract_webpage_content':
                    content = SearchResultParser._parse_content_extraction(msg)
                    if content and search_results:
                        # Update the most recent search result without content
                        SearchResultParser._attach_content_to_result(search_results, content)

        except Exception as e:
            logger.error(f"Error parsing agent messages: {e}", exc_info=True)

        return search_results

    @staticmethod
    def _parse_web_search_response(msg: Any) -> List[SearchResult]:
        """Parse web search tool response.

        Args:
            msg: Message object with web search results

        Returns:
            List of SearchResult objects
        """
        results = []

        try:
            content = msg.content

            # Handle string content
            if isinstance(content, str):
                try:
                    tool_results = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse web search JSON: {content[:100]}")
                    return results
            else:
                tool_results = content

            # Handle list of results
            if isinstance(tool_results, list):
                for item in tool_results:
                    if isinstance(item, dict):
                        result = SearchResultParser._dict_to_search_result(item)
                        if result:
                            results.append(result)

        except Exception as e:
            logger.error(f"Error parsing web search response: {e}")

        return results

    @staticmethod
    def _dict_to_search_result(data: Dict[str, Any]) -> Optional[SearchResult]:
        """Convert dictionary to SearchResult object.

        Args:
            data: Dictionary with search result data

        Returns:
            SearchResult object or None if invalid
        """
        try:
            return SearchResult(
                query=data.get('query', ''),
                title=data.get('title', ''),
                url=data.get('url', ''),
                snippet=data.get('snippet', ''),
                content=data.get('content', None)
            )
        except Exception as e:
            logger.error(f"Error creating SearchResult from dict: {e}")
            return None

    @staticmethod
    def _parse_content_extraction(msg: Any) -> Optional[str]:
        """Parse content extraction tool response.

        Args:
            msg: Message object with extracted content

        Returns:
            Extracted content string or None
        """
        try:
            content = msg.content

            # Content should be a string
            if isinstance(content, str):
                return content if content.strip() else None

            logger.warning(f"Unexpected content type: {type(content)}")
            return None

        except Exception as e:
            logger.error(f"Error parsing content extraction: {e}")
            return None

    @staticmethod
    def _attach_content_to_result(results: List[SearchResult], content: str) -> None:
        """Attach extracted content to the most recent result without content.

        Args:
            results: List of SearchResult objects
            content: Content to attach
        """
        for result in reversed(results):
            if not result.content:
                result.content = content
                logger.debug(f"Attached content to result: {result.url}")
                break


class AgentOutputParser:
    """Parses various types of agent outputs."""

    @staticmethod
    def extract_final_answer(messages: List[Any]) -> Optional[str]:
        """Extract the final answer from agent messages.

        Args:
            messages: List of messages from agent execution

        Returns:
            Final answer text or None
        """
        if not messages:
            return None

        try:
            last_msg = messages[-1]

            # Handle different content formats
            if hasattr(last_msg, 'content'):
                content = last_msg.content

                # List content (from tool responses)
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                        elif isinstance(item, dict) and item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                        else:
                            text_parts.append(str(item))
                    return ''.join(text_parts)

                # String content
                elif isinstance(content, str):
                    return content

            return str(last_msg)

        except Exception as e:
            logger.error(f"Error extracting final answer: {e}")
            return None

    @staticmethod
    def count_tool_calls(messages: List[Any]) -> Dict[str, int]:
        """Count tool calls by type in agent messages.

        Args:
            messages: List of messages from agent execution

        Returns:
            Dictionary mapping tool names to call counts
        """
        tool_counts = {}

        try:
            for msg in messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get('name', 'unknown')
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        except Exception as e:
            logger.error(f"Error counting tool calls: {e}")

        return tool_counts

    @staticmethod
    def extract_errors(messages: List[Any]) -> List[str]:
        """Extract error messages from agent execution.

        Args:
            messages: List of messages from agent execution

        Returns:
            List of error messages
        """
        errors = []

        try:
            for msg in messages:
                # Check for error in content
                if hasattr(msg, 'content'):
                    content_str = str(msg.content).lower()
                    if 'error' in content_str or 'exception' in content_str or 'failed' in content_str:
                        errors.append(str(msg.content))

                # Check for tool call errors
                if hasattr(msg, 'name') and hasattr(msg, 'content'):
                    if 'error' in str(msg.content).lower():
                        errors.append(f"{msg.name}: {msg.content}")

        except Exception as e:
            logger.error(f"Error extracting errors: {e}")

        return errors


# Convenience functions
def parse_search_results(messages: List[Any]) -> List[SearchResult]:
    """Parse search results from agent messages - convenience wrapper."""
    return SearchResultParser.parse_agent_messages(messages)


def extract_final_answer(messages: List[Any]) -> Optional[str]:
    """Extract final answer from agent messages - convenience wrapper."""
    return AgentOutputParser.extract_final_answer(messages)
