"""Agent nodes for the research workflow."""

import asyncio
from typing import List
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain.agents import create_agent

from src.state import ResearchState, ResearchPlan, SearchQuery, ReportSection
from src.utils.tools import get_research_tools
from src.config import config
from src.utils.credibility import CredibilityScorer
from src.utils.citations import CitationFormatter
from src.utils.deduplication import DeduplicationCache
from src.llm_tracker import estimate_tokens
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_llm(temperature: float = None, model_override: str = None):
    """Get LLM instance based on configuration.

    Args:
        temperature: Temperature for the LLM (defaults to config.llm_temperature)
        model_override: Optional model name to override config.model_name

    Returns:
        LLM instance (ChatOllama, ChatGoogleGenerativeAI, ChatOpenAI, or LM Studio)
    """
    model_name = model_override or config.model_name
    temp = temperature if temperature is not None else config.llm_temperature

    if config.model_provider == "ollama":
        logger.info(f"Using Ollama model: {model_name}")
        return ChatOllama(
            model=model_name,
            base_url=config.ollama_base_url,
            temperature=temp,
            num_ctx=config.context_window_size,
        )
    elif config.model_provider == "lmstudio":
        logger.info(f"Using LM Studio model: {model_name}")
        # LM Studio uses OpenAI-compatible API
        return ChatOpenAI(
            model=model_name or config.lmstudio_model_name,
            base_url=config.lmstudio_base_url,
            api_key="lm-studio",  # LM Studio doesn't require real API key
            temperature=temp,
            max_tokens=config.max_tokens_per_call
        )
    elif config.model_provider == "openai":
        logger.info(f"Using OpenAI model: {model_name}")
        return ChatOpenAI(
            model=model_name,
            base_url=config.openai_base_url,
            api_key=config.openai_api_key,
            temperature=temp,
            max_tokens=config.max_tokens_per_call
        )
    else:  # gemini
        logger.info(f"Using Gemini model: {model_name}")
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=config.google_api_key,
            temperature=temp
        )


class ResearchPlanner:
    """Autonomous agent responsible for planning research strategy."""

    def __init__(self):
        # Use planner-specific model if configured, otherwise fall back to default
        self.model_name = config.planner_model or config.model_name
        self.llm = None  # Lazy loading - only load when plan() is called
        # Note: Planning agent uses LLM directly with structured output for reliability
        # Tool calling works better for search/extraction tasks
        self.max_retries = config.max_retries
        logger.info(f"ResearchPlanner initialized (lazy load: {self.model_name})")

    def _ensure_llm_loaded(self):
        """Ensure LLM is loaded (lazy loading)."""
        if self.llm is None:
            logger.info(f"Loading Planner LLM: {self.model_name}")
            self.llm = get_llm(model_override=self.model_name)

    def unload_model(self):
        """Unload the LLM to free memory."""
        if self.llm is not None and config.model_provider == "ollama":
            try:
                import subprocess
                subprocess.run(["ollama", "stop", self.model_name], check=False, capture_output=True)
                logger.info(f"Unloaded Planner model: {self.model_name}")
            except Exception as e:
                logger.debug(f"Could not unload model: {e}")
            self.llm = None
        
    async def plan(self, state: ResearchState) -> dict:
        """Create a research plan with structured LLM output.

        Returns dict with updates that LangGraph will merge into state.
        """
        self._ensure_llm_loaded()  # Lazy load LLM
        logger.info(f"Planning research for: {state.research_topic}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research planner. Given a research topic, create a comprehensive research plan.

Your plan should include:
1. Clear research objectives (3-5 objectives)
2. Strategic search queries to gather information (up to {max_queries} queries)
   - Create diverse queries covering different aspects
   - Include both broad overview queries and specific deep-dive queries
   - Consider current trends, historical context, and future implications

   CRITICAL FOR RECENCY: To get the most recent information:
   - Include time-bound queries with "2024", "2025", "latest", "recent"
   - Add queries like "[topic] news 2024", "[topic] latest developments"
   - Include "[topic] recent research", "[topic] this year"
   - For weekly monitoring, add "[topic] this month", "[topic] this week"

   CRITICAL FOR SPECIFICITY - Find CONCRETE facts, not generic analysis:
   - Target AUTHORITATIVE sources: "BLS [topic]", "McKinsey report [topic] 2024"
   - Look for QUANTITATIVE data: "[topic] statistics 2024", "[topic] job losses numbers", "[topic] growth rate"
   - Find SPECIFIC events: "[topic] layoffs November 2024", "[topic] company announcements 2024"
   - Seek PROFESSIONAL analysis: "Brookings [topic]", "Pew Research [topic]", "[topic] economic impact"

   DOMAIN PRIORITIES (these give better results than arxiv):
   - Labor data: "Bureau of Labor Statistics", "unemployment rate", "job openings data"
   - Industry reports: "McKinsey", "BCG", "Deloitte insights", "Gartner analysis"
   - Business news: "Reuters [topic]", "Bloomberg [topic]", "WSJ [topic] 2024"
   - Think tanks: "Brookings Institution", "RAND Corporation", "Pew Research Center"
   - Company data: "[company name] layoffs 2024", "[company name] hiring AI"

   AVOID vague queries that return irrelevant academic papers

3. An outline for the final report (up to {max_sections} sections)

Be strategic and thorough. The search queries will be used by an autonomous agent that can:
- Execute web searches
- Extract full content from web pages
- Gather information iteratively

Design your queries to maximize information gathering, with emphasis on RECENT, SPECIFIC, QUANTITATIVE content from AUTHORITATIVE sources."""),
            ("human", """Research Topic: {topic}

Create a detailed research plan in JSON format:
{{
    "topic": "the research topic",
    "objectives": ["objective 1", "objective 2", ...],
    "search_queries": [
        {{"query": "search query 1", "purpose": "why this query"}},
        {{"query": "search query 2", "purpose": "why this query"}},
        ...
    ],
    "report_outline": ["section 1 title", "section 2 title", ...]
}}""")
        ])
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                chain = prompt | self.llm | JsonOutputParser()
                
                # Estimate input tokens
                input_text = f"{state.research_topic} {config.max_search_queries} {config.max_report_sections}"
                input_tokens = estimate_tokens(input_text)
                
                result = await chain.ainvoke({
                    "topic": state.research_topic,
                    "max_queries": config.max_search_queries,
                    "max_sections": config.max_report_sections
                })
                
                # Track LLM call
                duration = time.time() - start_time
                output_tokens = estimate_tokens(str(result))
                call_detail = {
                    'agent': 'ResearchPlanner',
                    'operation': 'plan',
                    'model': config.model_name,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'duration': round(duration, 2),
                    'attempt': attempt + 1
                }
                
                # Validate result structure
                if not all(key in result for key in ["topic", "objectives", "search_queries", "report_outline"]):
                    raise ValueError("Invalid plan structure returned")
                
                if not result["search_queries"]:
                    raise ValueError("No search queries generated")
                
                # Convert to ResearchPlan
                plan_data = result
                
                # Validate result structure
                if not all(key in plan_data for key in ["topic", "objectives", "search_queries", "report_outline"]):
                    raise ValueError("Invalid plan structure returned")
                
                if not plan_data["search_queries"]:
                    raise ValueError("No search queries generated")
                
                # Convert to ResearchPlan with HARD LIMITS enforced
                plan = ResearchPlan(
                    topic=plan_data["topic"],
                    objectives=plan_data["objectives"][:5],  # Max 5 objectives
                    search_queries=[
                        SearchQuery(query=sq["query"], purpose=sq["purpose"])
                        for sq in plan_data["search_queries"][:config.max_search_queries]
                    ],
                    report_outline=plan_data["report_outline"][:config.max_report_sections]
                )
                
                logger.info(f"Created plan with {len(plan.search_queries)} queries (enforced max: {config.max_search_queries})")
                logger.info(f"Report outline has {len(plan.report_outline)} sections (enforced max: {config.max_report_sections})")
                
                # Return dict updates - LangGraph merges into state
                return {
                    "plan": plan,
                    "current_stage": "searching",
                    "iterations": state.iterations + 1,
                    "llm_calls": state.llm_calls + 1,
                    "total_input_tokens": state.total_input_tokens + input_tokens,
                    "total_output_tokens": state.total_output_tokens + output_tokens,
                    "llm_call_details": state.llm_call_details + [call_detail]
                }
                
            except Exception as e:
                logger.warning(f"Planning attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Planning failed after {self.max_retries} attempts")
                    return {
                        "error": f"Planning failed: {str(e)}",
                        "iterations": state.iterations + 1
                    }
                else:
                    await asyncio.sleep(2 ** attempt)
        
        # Fallback if all retries exhausted
        return {
            "error": "Planning failed: Maximum retries exceeded",
            "iterations": state.iterations + 1
        }


class ResearchSearcher:
    """Autonomous agent responsible for executing research searches."""

    def __init__(self):
        # Use search-specific model if configured, otherwise fall back to default
        self.model_name = config.search_model or config.model_name
        self.llm = None  # Lazy loading
        self.tools = get_research_tools(agent_type="search")
        self.credibility_scorer = CredibilityScorer(enable_recency_scoring=config.enable_recency_scoring)
        self.dedup_cache = DeduplicationCache(window_days=config.deduplication_window_days) if config.enable_deduplication else None
        self.max_retries = config.max_retries
        logger.info(f"ResearchSearcher initialized (lazy load: {self.model_name}, dedup: {config.enable_deduplication})")

    def _ensure_llm_loaded(self):
        """Ensure LLM is loaded (lazy loading)."""
        if self.llm is None:
            logger.info(f"Loading Searcher LLM: {self.model_name}")
            self.llm = get_llm(temperature=config.synthesis_temperature, model_override=self.model_name)

    def unload_model(self):
        """Unload the LLM to free memory."""
        if self.llm is not None and config.model_provider == "ollama":
            try:
                import subprocess
                subprocess.run(["ollama", "stop", self.model_name], check=False, capture_output=True)
                logger.info(f"Unloaded Searcher model: {self.model_name}")
            except Exception as e:
                logger.debug(f"Could not unload model: {e}")
            self.llm = None
        
    async def search(self, state: ResearchState) -> dict:
        """Autonomously execute research searches using tools.

        The agent will decide which searches to perform, when to extract content,
        and how to gather comprehensive information.

        Returns dict with search results that LangGraph will merge into state.
        """
        self._ensure_llm_loaded()  # Lazy load LLM

        if not state.plan:
            return {"error": "No research plan available"}

        logger.info(f"Autonomous agent researching: {len(state.plan.search_queries)} planned queries")
        
        # Create system prompt for autonomous agent with config-based limits
        max_searches = config.max_search_queries
        max_results_per_search = config.max_search_results_per_query
        expected_total_results = max_searches * max_results_per_search
        
        system_prompt = f"""You are an expert research assistant with access to web search and content extraction tools.

Your task is to efficiently research the given topic by:
1. Executing the planned search queries (limit to {max_searches} searches maximum)
2. Extracting detailed content from the most relevant sources
3. Gathering sufficient information to answer the research objectives

Guidelines:
- Use web_search to find relevant sources (limit to {max_searches} searches, {max_results_per_search} results each)
- Use extract_webpage_content to read full articles from the top {expected_total_results} promising URLs
- Focus on authoritative, credible sources
- Prioritize quality over quantity
- Extract content from {expected_total_results} high-quality sources

When you have gathered sufficient information ({expected_total_results} search results with content extractions), respond with:
RESEARCH_COMPLETE: [brief summary of what you found]"""
        
        # Create autonomous agent using LangChain's create_agent
        agent_graph = create_agent(
            self.llm,
            self.tools,
            system_prompt=system_prompt
        )
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                # Prepare input
                objectives_text = "\n".join(f"- {obj}" for obj in state.plan.objectives)
                queries_text = "\n".join(
                    f"- {q.query} (Purpose: {q.purpose})" 
                    for q in state.plan.search_queries
                )
                
                # Estimate input tokens
                input_message = f"""Research Topic: {state.research_topic}

Research Objectives:
{objectives_text}

Planned Search Queries:
{queries_text}

Begin your research. Use the tools to gather comprehensive information."""
                
                input_tokens = estimate_tokens(input_message)
                
                # Execute autonomous research
                result = await agent_graph.ainvoke({
                    "messages": [{"role": "user", "content": input_message}]
                })
                
                # Track LLM call (approximation - agent may make multiple calls)
                duration = time.time() - start_time
                
                # Extract messages from result
                messages = result.get('messages', [])
                output_text = ""
                if messages:
                    output_text = str(messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1]))
                
                output_tokens = estimate_tokens(output_text)
                
                # Extract search results from messages using robust parser
                from src.utils.result_parser import parse_search_results

                search_results = parse_search_results(messages)
                
                logger.info(f"Autonomous agent collected {len(search_results)} results")
                
                if not search_results:
                    raise ValueError("Agent did not collect any search results")
            
                # Score all results first
                scored_results = self.credibility_scorer.score_search_results(search_results)

                # Extract topic keywords for relevance filtering
                topic_keywords = self._extract_topic_keywords(state.research_topic)
                logger.info(f"Topic keywords for relevance filtering: {topic_keywords}")

                # Filter by credibility score, age, and topic relevance
                filtered_scored = []
                age_filtered_count = 0
                relevance_filtered_count = 0
                homepage_filtered_count = 0

                for item in scored_results:
                    result = item['result']
                    cred = item['credibility']

                    # Check credibility score
                    if cred['score'] < config.min_credibility_score:
                        continue

                    # Check for generic homepages (no specific content path)
                    if hasattr(result, 'url'):
                        if self._is_generic_homepage(result.url):
                            homepage_filtered_count += 1
                            logger.debug(f"Filtered generic homepage: {result.url}")
                            continue

                    # POSITIVE FILTERING: Check topic relevance for ALL sources
                    # Require sources to contain keywords related to the research topic
                    if hasattr(result, 'title'):
                        title = getattr(result, 'title', '')
                        snippet = getattr(result, 'snippet', '')

                        if not self._is_source_relevant(title, snippet, topic_keywords):
                            relevance_filtered_count += 1
                            logger.debug(f"Filtered irrelevant source: {title[:100]}")
                            continue

                    # Check age if filtering is enabled
                    if config.max_source_age_days > 0 and 'recency' in cred:
                        recency_info = cred['recency']
                        age_days = recency_info.get('age_days')

                        # If we have age info and it's too old, skip it
                        if age_days is not None and age_days > config.max_source_age_days:
                            age_filtered_count += 1
                            logger.debug(f"Filtered out source older than {config.max_source_age_days} days: {age_days} days old")
                            continue

                    filtered_scored.append(item)

                # Extract filtered results and scores (already sorted by score, highest first)
                credibility_scores = [item['credibility'] for item in filtered_scored]
                sorted_results = [item['result'] for item in filtered_scored]

                # Apply deduplication if enabled (for weekly mode)
                dedup_filtered_count = 0
                if self.dedup_cache:
                    previous_hashes = self.dedup_cache.load_previous_hashes()
                    sorted_results, duplicates = self.dedup_cache.check_duplicates(sorted_results, previous_hashes)
                    dedup_filtered_count = len(duplicates)
                    # Update credibility scores to match filtered results
                    if dedup_filtered_count > 0:
                        # Rebuild credibility_scores for remaining sources
                        remaining_urls = {getattr(r, 'url', '') for r in sorted_results}
                        credibility_scores = [
                            item['credibility'] for item in filtered_scored
                            if getattr(item['result'], 'url', '') in remaining_urls
                        ]

                logger.info(f"Filtered {len(search_results)} -> {len(sorted_results)} results "
                           f"(min_credibility={config.min_credibility_score}, age_filtered={age_filtered_count}, "
                           f"relevance_filtered={relevance_filtered_count}, homepage_filtered={homepage_filtered_count}, "
                           f"dedup_filtered={dedup_filtered_count})")
                
                # Mark queries as completed
                for q in state.plan.search_queries:
                    q.completed = True
                
                call_detail = {
                    'agent': 'ResearchSearcher',
                    'operation': 'autonomous_search',
                    'model': config.model_name,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'duration': round(duration, 2),
                    'results_count': len(sorted_results),
                    'original_results_count': len(search_results),
                    'min_credibility_score': config.min_credibility_score,
                    'attempt': attempt + 1
                }
                
                # Return dict updates - LangGraph merges into state
                return {
                    "search_results": sorted_results,
                    "credibility_scores": credibility_scores,
                    "current_stage": "synthesizing",
                    "iterations": state.iterations + 1,
                    "llm_calls": state.llm_calls + 1,
                    "total_input_tokens": state.total_input_tokens + input_tokens,
                    "total_output_tokens": state.total_output_tokens + output_tokens,
                    "llm_call_details": state.llm_call_details + [call_detail]
                }
                
            except Exception as e:
                logger.warning(f"Search attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Search failed after {self.max_retries} attempts")
                    return {
                        "error": f"Search failed: {str(e)}",
                        "iterations": state.iterations + 1
                    }
                else:
                    await asyncio.sleep(2 ** attempt)
        
        # Fallback if all retries exhausted
        return {
            "error": "Search failed: Maximum retries exceeded",
            "iterations": state.iterations + 1
        }

    def _extract_topic_keywords(self, research_topic: str) -> List[str]:
        """Extract keywords from research topic for relevance filtering.

        Args:
            research_topic: The research topic string

        Returns:
            List of keywords extracted from the topic
        """
        # Convert to lowercase for matching
        topic_lower = research_topic.lower()

        # Split into words and filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
                      'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
                      'that', 'these', 'those', 'what', 'how', 'when', 'where', 'why'}

        # Extract words (minimum 3 characters)
        words = [w.strip('.,!?;:()[]{}"\'-') for w in topic_lower.split()]
        keywords = [w for w in words if len(w) >= 3 and w not in stop_words]

        # Also add common variations and related terms based on key topics
        # This helps catch relevant sources that use different terminology
        expanded_keywords = set(keywords)

        # If topic mentions AI/automation, add related terms
        if any(term in topic_lower for term in ['ai', 'artificial intelligence', 'automation', 'machine learning']):
            expanded_keywords.update(['ai', 'artificial', 'intelligence', 'automation', 'machine', 'learning',
                                     'algorithm', 'robot', 'automated', 'neural', 'deep learning'])

        # If topic mentions jobs/employment, add related terms
        if any(term in topic_lower for term in ['job', 'employment', 'work', 'career', 'labor', 'workforce']):
            expanded_keywords.update(['job', 'jobs', 'employment', 'work', 'worker', 'workers', 'career',
                                     'labor', 'labour', 'workforce', 'hiring', 'layoff', 'layoffs',
                                     'unemployment', 'occupation', 'wage', 'salary', 'employee', 'employer'])

        # If topic mentions market/economy, add related terms
        if any(term in topic_lower for term in ['market', 'economy', 'economic', 'business', 'industry']):
            expanded_keywords.update(['market', 'economy', 'economic', 'business', 'industry', 'sector',
                                     'commercial', 'trade', 'financial', 'corporate'])

        # If topic mentions impact/effect/change, add related terms
        if any(term in topic_lower for term in ['impact', 'effect', 'change', 'transform', 'disrupt']):
            expanded_keywords.update(['impact', 'effect', 'affect', 'change', 'changing', 'transform',
                                     'transformation', 'disrupt', 'disruption', 'shift'])

        return list(expanded_keywords)

    def _is_source_relevant(self, title: str, snippet: str, topic_keywords: List[str]) -> bool:
        """Check if a source is relevant to the research topic.

        Uses positive filtering - requires sources to contain topic-related keywords.

        Args:
            title: Source title
            snippet: Source snippet/description
            topic_keywords: List of keywords related to the topic

        Returns:
            True if source is relevant, False otherwise
        """
        if not title and not snippet:
            return False

        # Combine title and snippet for checking
        combined_text = f"{title} {snippet}".lower()

        # Count how many topic keywords appear in the source
        keyword_matches = sum(1 for keyword in topic_keywords if keyword in combined_text)

        # Require at least 2 keyword matches for relevance
        # This prevents false positives while catching relevant sources
        # Exception: Very specific keywords count as 1 match
        specific_keywords = ['unemployment', 'layoff', 'layoffs', 'automation', 'workforce',
                            'employment', 'artificial intelligence', 'machine learning']

        has_specific = any(kw in combined_text for kw in specific_keywords)

        # Source is relevant if:
        # - Has 2+ general keyword matches, OR
        # - Has 1+ specific keyword match
        is_relevant = keyword_matches >= 2 or (keyword_matches >= 1 and has_specific)

        return is_relevant

    def _is_generic_homepage(self, url: str) -> bool:
        """Check if URL is a generic homepage without specific content.

        Generic homepages are less useful as specific sources.

        Args:
            url: URL to check

        Returns:
            True if URL is a generic homepage, False otherwise
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/')

            # Homepage indicators:
            # 1. No path or just '/' or '/index.*'
            # 2. Very short paths without substantive content indicators
            if not path or path in ['', '/'] or path.startswith('/index'):
                return True

            # Allow specific content paths
            content_indicators = [
                '/article', '/blog', '/post', '/news', '/research', '/paper',
                '/report', '/insight', '/publication', '/study', '/analysis',
                '/featured', '/press', '/release', '/whitepaper', '/pdf',
                '/doc', '/archive', '/abs', '/content', '/resources'
            ]

            # If path contains content indicators, it's specific
            if any(indicator in path.lower() for indicator in content_indicators):
                return False

            # Check if path is just a category/section without specific article
            # e.g., /insights or /reports without a specific slug
            path_parts = [p for p in path.split('/') if p]

            # If path has only 1-2 parts and doesn't look like a specific article, consider it generic
            # Specific articles usually have longer paths or identifiable slugs
            if len(path_parts) <= 1:
                # Single-level paths like '/insights' or '/reports' are generic
                generic_sections = ['about', 'insights', 'reports', 'publications', 'resources',
                                  'news', 'blog', 'research', 'contact', 'careers', 'team']
                if path_parts and path_parts[0].lower() in generic_sections:
                    return True

            # If we have a reasonable path with multiple parts, it's probably specific
            return False

        except Exception as e:
            logger.debug(f"Error checking if URL is generic homepage: {e}")
            return False


class ResearchSynthesizer:
    """Autonomous agent responsible for synthesizing research findings."""

    def __init__(self):
        # Use synthesis-specific model if configured, otherwise fall back to summarization_model
        self.model_name = config.synthesis_model or config.summarization_model
        self.llm = None  # Lazy loading
        self.tools = get_research_tools(agent_type="synthesis")
        self.max_retries = config.max_retries
        logger.info(f"ResearchSynthesizer initialized (lazy load: {self.model_name})")

    def _ensure_llm_loaded(self):
        """Ensure LLM is loaded (lazy loading)."""
        if self.llm is None:
            logger.info(f"Loading Synthesizer LLM: {self.model_name}")
            self.llm = get_llm(temperature=config.synthesis_temperature, model_override=self.model_name)

    def unload_model(self):
        """Unload the LLM to free memory."""
        if self.llm is not None and config.model_provider == "ollama":
            try:
                import subprocess
                subprocess.run(["ollama", "stop", self.model_name], check=False, capture_output=True)
                logger.info(f"Unloaded Synthesizer model: {self.model_name}")
            except Exception as e:
                logger.debug(f"Could not unload model: {e}")
            self.llm = None
        
    async def synthesize(self, state: ResearchState) -> dict:
        """Autonomously synthesize key findings using tools and reasoning.

        Returns dict with key findings that LangGraph will merge into state.
        """
        self._ensure_llm_loaded()  # Lazy load LLM

        logger.info(f"Synthesizing findings from {len(state.search_results)} results")

        if not state.search_results:
            return {"error": "No search results to synthesize"}
        
        # Create system prompt for autonomous synthesis agent
        system_prompt = """You are an expert research synthesis agent. Your task is to analyze search results and extract key findings.

You have access to the extract_insights_from_text tool which can help extract specific insights from text.

IMPORTANT: Each source has a credibility score (HIGH/MEDIUM/LOW) and score (0-100). 
- PRIORITIZE information from HIGH-credibility sources (score ≥70)
- When sources contradict each other, trust HIGH-credibility sources over MEDIUM or LOW
- Use MEDIUM-credibility sources (score 40-69) to supplement but not override HIGH-credibility sources
- Be cautious with LOW-credibility sources (score <40) - only use if no other sources are available

For each finding:
- Summarize the key insight
- Note which sources support it (prefer citing high-credibility sources)
- Identify any contradictions or debates (resolve using credibility hierarchy)
- Be concise but comprehensive

Focus on the most important and relevant information from the most credible sources. When ready, return your findings as a JSON array of strings."""
        
        # Create autonomous synthesis agent
        agent_graph = create_agent(
            self.llm,
            self.tools,
            system_prompt=system_prompt
        )
        
        # Progressive truncation strategy
        max_results = 20
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                # Adjust result count based on attempt
                current_max = max(5, max_results - (attempt * 5))
                
                # Prepare search results text with credibility information
                results_to_use = state.search_results[:current_max]
                credibility_scores_to_use = state.credibility_scores[:current_max] if state.credibility_scores else []
                
                results_text = "\n\n".join([
                    f"[{i+1}] {r.title}\n"
                    f"URL: {r.url}\n"
                    f"Credibility: {cred.get('level', 'unknown').upper()} (Score: {cred.get('score', 'N/A')}/100) - {', '.join(cred.get('factors', []))}\n"
                    f"Snippet: {r.snippet}\n" +
                    (f"Content: {r.content[:300]}..." if r.content else "")
                    for i, (r, cred) in enumerate(zip(results_to_use, credibility_scores_to_use))
                ])
                
                # If credibility scores don't match (shouldn't happen, but handle gracefully)
                if len(results_to_use) != len(credibility_scores_to_use):
                    # Fallback: format without credibility if mismatch
                    results_text = "\n\n".join([
                        f"[{i+1}] {r.title}\nURL: {r.url}\nSnippet: {r.snippet}\n" +
                        (f"Content: {r.content[:300]}..." if r.content else "")
                        for i, r in enumerate(results_to_use)
                    ])
                
                # Prepare input message for the autonomous agent
                input_message = f"""Research Topic: {state.research_topic}

Search Results:
{results_text}

Please analyze these search results and extract key findings. You may use the extract_insights_from_text tool to help identify important insights. Return your findings as a JSON array of strings."""
                
                # Estimate input tokens
                input_tokens = estimate_tokens(input_message)
                
                # Execute autonomous synthesis
                result = await agent_graph.ainvoke({
                    "messages": [{"role": "user", "content": input_message}]
                })
                
                # Track LLM call
                duration = time.time() - start_time
                
                # Extract final response using robust parser
                from src.utils.result_parser import extract_final_answer

                messages = result.get('messages', [])
                output_text = extract_final_answer(messages) or ""
                
                output_tokens = estimate_tokens(output_text)
                
                call_detail = {
                    'agent': 'ResearchSynthesizer',
                    'operation': 'autonomous_synthesis',
                    'model': config.summarization_model,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'duration': round(duration, 2),
                    'attempt': attempt + 1
                }
                
                # Parse the JSON response
                import json
                import re
                
                # Try to extract JSON array from the response
                json_match = re.search(r'\[(.*?)\]', output_text, re.DOTALL)
                
                key_findings = []
                if json_match:
                    try:
                        findings = json.loads(json_match.group(0))
                        if isinstance(findings, list):
                            key_findings = [
                                str(f)  # Convert all items to strings (handles int, dict, etc.)
                                for f in findings
                            ]
                        else:
                            key_findings = [str(findings)]
                    except json.JSONDecodeError:
                        pass
                
                # If JSON parsing failed or empty, use fallback extraction
                if not key_findings:
                    # Look for bullet points or numbered items
                    lines = output_text.split('\n')
                    for line in lines:
                        line = line.strip().lstrip('-').lstrip('*').lstrip('>').strip()
                        # Remove numbering like "1.", "2.", etc.
                        line = re.sub(r'^\d+\.\s*', '', line)
                        if len(line) > 30 and not line.startswith('[') and not line.startswith(']'):
                            key_findings.append(line)
                    
                    # Limit to reasonable number
                    key_findings = key_findings[:15]
                
                # If still empty, create basic findings from search results
                if not key_findings and state.search_results:
                    logger.warning("Agent produced no findings, creating basic ones from results")
                    key_findings = [
                        f"{r.title}: {r.snippet[:100]}..."
                        for r in state.search_results[:10]
                        if r.snippet
                    ]
                
                logger.info(f"Extracted {len(key_findings)} key findings")
                
                # Return dict updates - LangGraph merges into state
                return {
                    "key_findings": key_findings,
                    "current_stage": "reporting",
                    "iterations": state.iterations + 1,
                    "llm_calls": state.llm_calls + 1,
                    "total_input_tokens": state.total_input_tokens + input_tokens,
                    "total_output_tokens": state.total_output_tokens + output_tokens,
                    "llm_call_details": state.llm_call_details + [call_detail]
                }
                
            except Exception as e:
                logger.warning(f"Synthesis attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Synthesis failed after {self.max_retries} attempts")
                    return {
                        "error": f"Synthesis failed: {str(e)}",
                        "iterations": state.iterations + 1
                    }
                else:
                    await asyncio.sleep(2 ** attempt)
        
        # Fallback if all retries exhausted
        return {
            "error": "Synthesis failed: Maximum retries exceeded",
            "iterations": state.iterations + 1
        }


class ReportWriter:
    """Autonomous agent responsible for writing research reports."""

    def __init__(self, citation_style: str = None):
        # Use writing-specific model if configured, otherwise fall back to default
        self.model_name = config.writing_model or config.model_name
        self.llm = None  # Lazy loading
        self.tools = get_research_tools(agent_type="writing")
        self.max_retries = config.max_retries
        self.citation_style = citation_style or config.citation_style
        self.citation_formatter = CitationFormatter()
        logger.info(f"ReportWriter initialized (lazy load: {self.model_name})")

    def _ensure_llm_loaded(self):
        """Ensure LLM is loaded (lazy loading)."""
        if self.llm is None:
            logger.info(f"Loading Writer LLM: {self.model_name}")
            self.llm = get_llm(model_override=self.model_name)

    def unload_model(self):
        """Unload the LLM to free memory."""
        if self.llm is not None and config.model_provider == "ollama":
            try:
                import subprocess
                subprocess.run(["ollama", "stop", self.model_name], check=False, capture_output=True)
                logger.info(f"Unloaded Writer model: {self.model_name}")
            except Exception as e:
                logger.debug(f"Could not unload model: {e}")
            self.llm = None
        
    async def write_report(self, state: ResearchState) -> dict:
        """Write the final research report with validation and retry.

        Returns dict with report data that LangGraph will merge into state.
        """
        self._ensure_llm_loaded()  # Lazy load LLM

        logger.info("Writing final report")

        if not state.plan or not state.key_findings:
            return {"error": "Insufficient data for report generation"}

        # CREATE MASTER SOURCE LIST FIRST - prevents citation numbering mismatches
        # Build a single numbered source list that ALL sections will use
        master_sources = []
        master_source_info = []  # For References section
        seen_urls = set()

        if state.search_results:
            for i, result in enumerate(state.search_results[:20]):  # Top 20 sources
                if hasattr(result, 'url') and result.url and result.url not in seen_urls:
                    seen_urls.add(result.url)
                    master_sources.append(result)
                    # Store info for References section
                    title = getattr(result, 'title', '')
                    cred_info = state.credibility_scores[i] if state.credibility_scores and i < len(state.credibility_scores) else {}
                    date = ''
                    if 'recency' in cred_info and 'date' in cred_info['recency']:
                        date = cred_info['recency']['date']
                    master_source_info.append({
                        'url': result.url,
                        'title': title,
                        'date': date,
                        'number': len(master_sources)  # 1-indexed
                    })

        logger.info(f"Created master source list with {len(master_sources)} sources for consistent citation numbering")

        # Track total LLM calls for report generation
        report_llm_calls = 0
        report_input_tokens = 0
        report_output_tokens = 0
        report_call_details = []
        
        for attempt in range(self.max_retries):
            try:
                # Generate each section with retry - using MASTER source list for consistency
                report_sections = []
                for section_title in state.plan.report_outline:
                    section, section_tokens = await self._write_section(
                        state.research_topic,
                        section_title,
                        state.key_findings,
                        master_sources  # Use master list so all sections have same numbering
                    )
                    if section:
                        report_sections.append(section)
                        if section_tokens:
                            report_llm_calls += 1
                            report_input_tokens += section_tokens['input_tokens']
                            report_output_tokens += section_tokens['output_tokens']
                            report_call_details.append(section_tokens)
                
                # Validate minimum quality
                if not report_sections:
                    raise ValueError("No report sections generated")
                
                # Create temporary state for compilation
                temp_state = ResearchState(
                    research_topic=state.research_topic,
                    plan=state.plan,
                    report_sections=report_sections
                )

                # Compile final report with master source list for consistent References
                final_report = self._compile_report(temp_state, master_source_info)
                
                # Format citations in specified style with dates
                if state.search_results:
                    final_report = self.citation_formatter.update_report_citations(
                        final_report,
                        style=self.citation_style,
                        search_results=state.search_results,
                        credibility_scores=state.credibility_scores
                    )

                    # Verify citation relevance and log warnings about potential mismatches
                    citation_warnings = self.citation_formatter.verify_citation_relevance(
                        final_report,
                        search_results=state.search_results
                    )
                    if citation_warnings:
                        logger.warning(f"Found {len(citation_warnings)} potential citation mismatches - review recommended")
                        for warning in citation_warnings[:5]:  # Log first 5 warnings
                            logger.warning(f"  [{warning['citation']}] {warning['source_title']}: {warning['claim'][:80]}...")

                # Add credibility information to report if available
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
                
                logger.info(f"Report generation complete: {len(final_report)} chars")
                
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
                logger.warning(f"Report attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Report generation failed after {self.max_retries} attempts")
                    return {
                        "error": f"Report writing failed: {str(e)}",
                        "iterations": state.iterations + 1
                    }
                else:
                    await asyncio.sleep(2 ** attempt)
        
        # Fallback if all retries exhausted
        return {
            "error": "Report generation failed: Maximum retries exceeded",
            "iterations": state.iterations + 1
        }
    
    async def _write_section(
        self,
        topic: str,
        section_title: str,
        findings: List[str],
        search_results: List
    ) -> tuple:
        """Autonomously write a single report section using tools."""
        logger.info(f"Writing section: {section_title}")
        
        # Create system prompt for section writing
        system_prompt = """You are an expert research writer agent. Write comprehensive, well-structured sections for research reports.

You have access to:
- format_citation: Format citations in academic styles
- validate_section_quality: Check if your section meets quality standards

Requirements:
- Minimum {min_words} words
- Use clear, academic language
- Include specific facts and data from the provided sources
- Cite sources using inline citations [1], [2], [3], etc.
- Use markdown formatting
- Be objective and balanced

CRITICAL SPECIFICITY REQUIREMENTS - NO GENERIC CONTENT:
1. Include CONCRETE facts: dates, numbers, percentages, company names, specific events
2. BAD: "Recent layoffs in tech companies" GOOD: "Google laid off 12,000 in January 2024 [1]"
3. BAD: "AI is transforming jobs" GOOD: "BLS reports 4.7% unemployment in tech sector, down from 5.2% in Q3 2024 [3]"
4. EVERY major claim needs: WHO (company/org), WHAT (specific action), WHEN (exact date), HOW MUCH (numbers)
5. If sources don't provide specific facts, DON'T write generic statements - skip that point
6. Generic knowledge without citations is UNACCEPTABLE - use sources or nothing

CRITICAL SOURCE RELEVANCE RULE - NO FORCED CITATIONS:
1. ONLY cite sources that are DIRECTLY relevant to the specific claim you're making
2. DO NOT invent tenuous connections to force irrelevant sources into the narrative
3. BAD: "Research from the Voice Privacy Challenge highlights AI's privacy protection capabilities [14]" - when writing about job market
4. GOOD: Simply omit claims that aren't supported by relevant sources
5. It is BETTER to have fewer citations to highly relevant sources than to force irrelevant sources with invented connections
6. If a source doesn't directly support a claim about the topic, DON'T use it

CRITICAL CITATION RULES - CITATION INTEGRITY IS PARAMOUNT:
1. You will be provided with a FIXED numbered list of sources (e.g., [1] through [15])
2. Use inline citations [1], [2], etc. ONLY for sources in the provided list
3. NEVER cite a source number that doesn't exist in the list (e.g., if list goes to [15], don't cite [16], [17], [19])
4. NEVER make up, invent, or hallucinate source numbers
5. DO NOT write out URLs or create a References section (handled separately)
6. If you can't find a source for a claim, either:
   - Find it in the provided sources, OR
   - Omit the claim, OR
   - State it as general knowledge without citation
7. Every numbered citation MUST correspond to an actual source in the provided list

VIOLATION OF THESE RULES SEVERELY DAMAGES REPORT CREDIBILITY.

You may use validate_section_quality to check your work before finalizing."""
        
        # Create autonomous writing agent
        agent_graph = create_agent(
            self.llm,
            self.tools,
            system_prompt=system_prompt
        )
        
        try:
            start_time = time.time()
            
            # Count actual sources provided
            num_sources = min(len(search_results), 20)

            # Prepare input message
            input_message = f"""Research Topic: {topic}
Section Title: {section_title}
Minimum Words: {config.min_section_words}

Key Findings:
{chr(10).join(f"- {f}" for f in findings)}

AVAILABLE SOURCES (cite these by number - references will be added at the end):
{chr(10).join(f"[{i+1}] {r.title}" + chr(10) + f"    URL: {r.url}" + chr(10) + f"    Snippet: {r.snippet[:200]}..." for i, r in enumerate(search_results[:20]))}

CRITICAL INSTRUCTIONS FOR CITATIONS:
1. The source list above contains sources numbered [1] through [{num_sources}]
2. You MAY ONLY cite sources [1] through [{num_sources}] - these are the ONLY valid citation numbers
3. NEVER cite source numbers higher than [{num_sources}] (e.g., don't cite [19] if list only goes to [15])
4. DO NOT include a References section in your output (it will be added later)
5. DO NOT write out full URLs in the text
6. Every citation number MUST match a source in the list above
7. If you need a fact not in the sources, either omit it or state it without citation

REMINDER: Your citation numbers MUST be between [1] and [{num_sources}]. Any number outside this range is INVALID.

Write a comprehensive, well-researched section using inline citations [1] through [{num_sources}] ONLY."""
            
            # Estimate input tokens
            input_tokens = estimate_tokens(input_message)
            
            # Execute autonomous section writing
            result = await agent_graph.ainvoke({
                "messages": [{"role": "user", "content": input_message}]
            })
            
            # Extract content from result
            messages = result.get('messages', [])
            content = ""
            if messages:
                last_msg = messages[-1]
                # Handle different content formats
                if hasattr(last_msg, 'content'):
                    msg_content = last_msg.content
                    # If content is a list (like from tool responses), extract text
                    if isinstance(msg_content, list):
                        content = ""
                        for item in msg_content:
                            if isinstance(item, dict) and 'text' in item:
                                content += item['text']
                            elif isinstance(item, dict) and 'type' in item and item['type'] == 'text':
                                content += item.get('text', '')
                            else:
                                content += str(item)
                    else:
                        content = str(msg_content)
                else:
                    content = str(last_msg)
            
            # Track LLM call
            duration = time.time() - start_time
            output_tokens = estimate_tokens(content)
            call_detail = {
                'agent': 'ReportWriter',
                'operation': f'write_section_{section_title[:30]}',
                'model': config.model_name,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'duration': round(duration, 2)
            }
            
            # Extract cited sources
            import re
            citations = re.findall(r'\[(\d+)\]', content)
            source_urls = []
            for cite_num in set(citations):
                idx = int(cite_num) - 1
                if 0 <= idx < len(search_results):
                    source_urls.append(search_results[idx].url)
            
            section = ReportSection(
                title=section_title,
                content=content,
                sources=source_urls
            )
            
            return section, call_detail
            
        except Exception as e:
            logger.error(f"Error writing section '{section_title}': {str(e)}")
            return None, None
    
    def _compile_report(self, state: ResearchState, master_source_info: list = None) -> str:
        """Compile all sections into final report with consistent source numbering.

        Args:
            state: Research state with sections
            master_source_info: Pre-built master source list with numbering

        Returns:
            Compiled report with consistent citations
        """
        report_sections = getattr(state, 'report_sections', []) or []

        # Use master source info for accurate count
        source_count = len(master_source_info) if master_source_info else 0
        
        report_parts = [
            f"# {state.research_topic}\n",
            f"**Deep Research Report**\n",
            f"\n## Executive Summary\n",
            f"This report provides a comprehensive analysis of {state.research_topic}. ",
            f"The research was conducted across **{source_count} sources** ",
            f"and synthesized into **{len(report_sections)} key sections**.\n",
            f"\n## Research Objectives\n"
        ]
        
        if state.plan and hasattr(state.plan, 'objectives'):
            for i, obj in enumerate(state.plan.objectives, 1):
                report_parts.append(f"{i}. {obj}\n")
        
        report_parts.append("\n---\n")
        
        # Add all sections
        has_references_section = False
        for section in report_sections:
            # Check if content already starts with the title as a heading
            content = section.content.strip()
            
            # Check if this section contains References
            if "## References" in content or section.title.lower() == "references":
                has_references_section = True
            
            if content.startswith(f"## {section.title}"):
                # Content already has heading, use as-is
                report_parts.append(f"\n{content}\n\n")
            else:
                # Add heading before content
                report_parts.append(f"\n## {section.title}\n\n")
                report_parts.append(content)
                report_parts.append("\n")
        
        # Add References section using master_source_info for consistent numbering
        if not has_references_section:
            report_parts.append("\n---\n\n## References\n\n")

            if master_source_info:
                from src.utils.citations import CitationFormatter
                formatter = CitationFormatter()

                # Use master_source_info which has pre-assigned numbers matching text citations
                for source in master_source_info:
                    num = source['number']
                    url = source['url']
                    title = source['title']
                    date = source['date']

                    # Format citation with date if available
                    citation = formatter.format_apa(url, title, date=date)
                    report_parts.append(f"{num}. {citation}\n")

                logger.info(f"Added {len(master_source_info)} references with consistent numbering")
            else:
                report_parts.append("*No sources were available for this research.*\n")
        
        return "".join(report_parts)

