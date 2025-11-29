"""Configuration management for the Deep Research Agent."""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


# Research Mode Presets
RESEARCH_MODES: Dict[str, Dict[str, Any]] = {
    'weekly': {
        'max_source_age_days': 14,
        'enable_deduplication': True,
        'deduplication_window_days': 30,
        'primary_search_apis': ['serper', 'tavily'],
        'fallback_search_apis': ['brave', 'duckduckgo'],
        'enable_time_bound_searches': True,
        'search_cache_ttl_hours': 6,
        'enable_cloud_apis': True,
        'enable_recency_scoring': True,
        'min_credibility_score': 50,
        'description': 'Weekly monitoring: recent news (<14 days), deduplication, fast updates'
    },
    'general': {
        'max_source_age_days': 365,
        'enable_deduplication': False,
        'deduplication_window_days': 0,
        'primary_search_apis': ['serper', 'tavily', 'brave'],
        'fallback_search_apis': ['duckduckgo'],
        'enable_time_bound_searches': False,
        'search_cache_ttl_hours': 24,
        'enable_cloud_apis': True,
        'enable_recency_scoring': True,
        'min_credibility_score': 40,
        'description': 'General research: comprehensive, no date limits, all sources'
    },
    'privacy': {
        'max_source_age_days': 365,
        'enable_deduplication': False,
        'deduplication_window_days': 0,
        'primary_search_apis': ['duckduckgo'],
        'fallback_search_apis': [],
        'enable_time_bound_searches': False,
        'search_cache_ttl_hours': 24,
        'enable_cloud_apis': False,
        'enable_recency_scoring': True,
        'min_credibility_score': 40,
        'force_local_models': True,
        'disable_api_search': True,
        'description': 'Privacy mode: local models, no external APIs, no tracking'
    }
}


class ResearchConfig(BaseModel):
    """Configuration for the research agent."""

    # Research Mode Configuration
    research_mode: str = Field(
        default=os.getenv("RESEARCH_MODE", "general"),
        description="Research mode: 'weekly' (monitoring), 'general' (comprehensive), or 'privacy' (local-only)"
    )

    # Model Provider Configuration
    model_provider: str = Field(
        default=os.getenv("MODEL_PROVIDER", "gemini"),
        description="Model provider: 'gemini', 'ollama', 'openai', or 'lmstudio'"
    )

    # API Keys
    google_api_key: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", ""),
        description="Google/Gemini API key (required if using Gemini)"
    )

    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", ""),
        description="OpenAI API key (required if using OpenAI)"
    )

    openai_base_url: str = Field(
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        description="OpenAI API base URL (for custom endpoints/proxies)"
    )

    # Ollama Configuration
    ollama_base_url: str = Field(
        default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        description="Ollama server URL"
    )

    # LM Studio Configuration
    lmstudio_base_url: str = Field(
        default=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
        description="LM Studio server URL (OpenAI-compatible endpoint)"
    )

    lmstudio_model_name: str = Field(
        default=os.getenv("LMSTUDIO_MODEL_NAME", "local-model"),
        description="LM Studio model name (must match loaded model)"
    )
    
    # Model Configuration
    model_name: str = Field(
        default=os.getenv("MODEL_NAME", "gemini-2.5-flash"),
        description="Model to use for research and generation"
    )

    summarization_model: str = Field(
        default=os.getenv("SUMMARIZATION_MODEL", "gemini-2.5-flash"),
        description="Model for summarizing search results (faster/cheaper)"
    )

    # Agent-Specific Model Configuration (optional overrides)
    planner_model: Optional[str] = Field(
        default=os.getenv("PLANNER_MODEL", None),
        description="Model for planning agent (defaults to model_name if not set)"
    )

    search_model: Optional[str] = Field(
        default=os.getenv("SEARCH_MODEL", None),
        description="Model for search agent (defaults to model_name if not set)"
    )

    synthesis_model: Optional[str] = Field(
        default=os.getenv("SYNTHESIS_MODEL", None),
        description="Model for synthesis agent (defaults to summarization_model if not set)"
    )

    writing_model: Optional[str] = Field(
        default=os.getenv("WRITING_MODEL", None),
        description="Model for writing agent (defaults to model_name if not set)"
    )

    # NEW: Specialized Model Configuration (DR Tulu & OLMo)
    use_dr_tulu_writer: bool = Field(
        default=os.getenv("USE_DR_TULU_WRITER", "false").lower() == "true",
        description="Use DR Tulu-8B for report writing (88.6% citation precision)"
    )

    dr_tulu_endpoint: str = Field(
        default=os.getenv("DR_TULU_ENDPOINT", "http://localhost:30001/v1"),
        description="DR Tulu VLLM server endpoint"
    )

    use_olmo_critic: bool = Field(
        default=os.getenv("USE_OLMO_CRITIC", "false").lower() == "true",
        description="Use OLMo 3 32B Think for enhanced research critique"
    )

    olmo_endpoint: str = Field(
        default=os.getenv("OLMO_ENDPOINT", "http://localhost:30002/v1"),
        description="OLMo 3 32B Think VLLM server endpoint"
    )

    # Search Configuration
    max_search_queries: int = Field(
        default=int(os.getenv("MAX_SEARCH_QUERIES", "5")),
        description="Maximum number of search queries to generate (increased for better coverage)"
    )

    max_search_results_per_query: int = Field(
        default=int(os.getenv("MAX_SEARCH_RESULTS_PER_QUERY", "5")),
        description="Maximum results to fetch per search query (increased for source diversity)"
    )

    max_parallel_searches: int = Field(
        default=int(os.getenv("MAX_PARALLEL_SEARCHES", "3")),
        description="Maximum number of parallel search operations"
    )

    enable_time_bound_searches: bool = Field(
        default=os.getenv("ENABLE_TIME_BOUND_SEARCHES", "true").lower() == "true",
        description="Enable time-bound searches with recency keywords (latest, recent, 2024)"
    )

    max_source_age_days: int = Field(
        default=int(os.getenv("MAX_SOURCE_AGE_DAYS", "365")),
        description="Maximum age of sources in days (0 = no filter)"
    )

    # Deduplication Configuration
    enable_deduplication: bool = Field(
        default=os.getenv("ENABLE_DEDUPLICATION", "false").lower() == "true",
        description="Enable deduplication to avoid repeating sources from previous reports"
    )

    deduplication_window_days: int = Field(
        default=int(os.getenv("DEDUPLICATION_WINDOW_DAYS", "30")),
        description="How many days back to check for duplicate sources"
    )

    # Search API Configuration
    serper_api_key: str = Field(
        default_factory=lambda: os.getenv("SERPER_API_KEY", ""),
        description="Serper API key for Google Search"
    )

    tavily_api_key: str = Field(
        default_factory=lambda: os.getenv("TAVILY_API_KEY", ""),
        description="Tavily API key for research search"
    )

    brave_api_key: str = Field(
        default_factory=lambda: os.getenv("BRAVE_API_KEY", ""),
        description="Brave Search API key"
    )

    primary_search_apis: List[str] = Field(
        default_factory=lambda: os.getenv("PRIMARY_SEARCH_APIS", "").split(",") if os.getenv("PRIMARY_SEARCH_APIS") else [],
        description="Primary search APIs to use (serper, tavily, brave, duckduckgo)"
    )

    fallback_search_apis: List[str] = Field(
        default_factory=lambda: os.getenv("FALLBACK_SEARCH_APIS", "").split(",") if os.getenv("FALLBACK_SEARCH_APIS") else [],
        description="Fallback search APIs if primary fails"
    )

    search_cache_ttl_hours: int = Field(
        default=int(os.getenv("SEARCH_CACHE_TTL_HOURS", "24")),
        description="Search result cache TTL in hours"
    )

    enable_cloud_apis: bool = Field(
        default=os.getenv("ENABLE_CLOUD_APIS", "true").lower() == "true",
        description="Enable cloud-based search APIs (disable for privacy mode)"
    )

    # Credibility Configuration
    min_credibility_score: int = Field(
        default=int(os.getenv("MIN_CREDIBILITY_SCORE", "40")),
        description="Minimum credibility score (0-100) to filter low-quality sources"
    )
    
    # Report Configuration
    max_report_sections: int = Field(
        default=int(os.getenv("MAX_REPORT_SECTIONS", "8")),
        description="Maximum number of sections in the final report"
    )
    
    min_section_words: int = Field(
        default=int(os.getenv("MIN_SECTION_WORDS", "200")),
        description="Minimum words per section"
    )

    # Citation Configuration
    citation_style: str = Field(
        default=os.getenv("CITATION_STYLE", "apa"),
        description="Citation style (apa, mla, chicago, ieee)"
    )

    # NEW: Specialized Search Configuration
    enable_arxiv_search: bool = Field(
        default=os.getenv("ENABLE_ARXIV_SEARCH", "true").lower() == "true",
        description="Enable arXiv academic paper search"
    )

    enable_ssrn_search: bool = Field(
        default=os.getenv("ENABLE_SSRN_SEARCH", "true").lower() == "true",
        description="Enable SSRN paper search"
    )

    enable_hackernews_search: bool = Field(
        default=os.getenv("ENABLE_HACKERNEWS_SEARCH", "true").lower() == "true",
        description="Enable Hacker News search"
    )

    enable_reddit_search: bool = Field(
        default=os.getenv("ENABLE_REDDIT_SEARCH", "true").lower() == "true",
        description="Enable Reddit search"
    )

    # Reddit API (optional - for better rate limits)
    reddit_client_id: str = Field(
        default=os.getenv("REDDIT_CLIENT_ID", ""),
        description="Reddit API client ID (optional)"
    )

    reddit_client_secret: str = Field(
        default=os.getenv("REDDIT_CLIENT_SECRET", ""),
        description="Reddit API client secret (optional)"
    )

    reddit_user_agent: str = Field(
        default=os.getenv("REDDIT_USER_AGENT", "deep-research-agent/1.0"),
        description="Reddit API user agent"
    )

    # NEW: RSS/Newsletter Ingestion
    enable_rss_feeds: bool = Field(
        default=os.getenv("ENABLE_RSS_FEEDS", "true").lower() == "true",
        description="Enable RSS/Atom feed ingestion for early signal detection"
    )

    rss_feed_days: int = Field(
        default=int(os.getenv("RSS_FEED_DAYS", "7")),
        description="Number of days back to fetch RSS items"
    )

    rss_max_items_per_feed: int = Field(
        default=int(os.getenv("RSS_MAX_ITEMS_PER_FEED", "10")),
        description="Maximum items to fetch per RSS feed"
    )

    rss_priority_filter: Optional[str] = Field(
        default=os.getenv("RSS_PRIORITY_FILTER", None),
        description="Filter RSS feeds by priority (high, medium, low, or None for all)"
    )

    enabled_rss_feeds: Optional[List[str]] = Field(
        default=None,
        description="Comma-separated list of specific RSS feeds to enable (None = all based on priority filter). Example: 'openai_blog,anthropic_blog,arxiv_cs_ai'"
    )

    disabled_rss_feeds: List[str] = Field(
        default_factory=list,
        description="Comma-separated list of RSS feeds to explicitly disable. Example: 'venturebeat_ai,mit_tech_ai'"
    )

    custom_rss_feeds: Optional[str] = Field(
        default=os.getenv("CUSTOM_RSS_FEEDS", None),
        description="JSON string of custom RSS feeds to add. Example: '{\"my_feed\": {\"url\": \"https://example.com/feed.xml\", \"description\": \"My Feed\", \"priority\": \"high\"}}'"
    )

    # NEW: Credibility & Quality
    detect_consulting_reports: bool = Field(
        default=os.getenv("DETECT_CONSULTING_REPORTS", "true").lower() == "true",
        description="Detect and prioritize consulting firm reports"
    )

    prioritize_academic_sources: bool = Field(
        default=os.getenv("PRIORITIZE_ACADEMIC_SOURCES", "true").lower() == "true",
        description="Prioritize academic sources in credibility scoring"
    )

    enable_recency_scoring: bool = Field(
        default=os.getenv("ENABLE_RECENCY_SCORING", "true").lower() == "true",
        description="Enable recency scoring to prioritize more recent sources"
    )

    # NEW: Rate Limiting & Timeouts
    web_request_timeout: int = Field(
        default=int(os.getenv("WEB_REQUEST_TIMEOUT", "10")),
        description="Web request timeout in seconds"
    )

    search_rate_limit_seconds: float = Field(
        default=float(os.getenv("SEARCH_RATE_LIMIT_SECONDS", "2.0")),
        description="Minimum seconds between search requests"
    )

    content_extraction_timeout: int = Field(
        default=int(os.getenv("CONTENT_EXTRACTION_TIMEOUT", "15")),
        description="Content extraction timeout in seconds"
    )

    max_retries: int = Field(
        default=int(os.getenv("MAX_RETRIES", "3")),
        description="Maximum retries for failed operations"
    )

    # NEW: Caching Configuration
    enable_cache: bool = Field(
        default=os.getenv("ENABLE_CACHE", "true").lower() == "true",
        description="Enable research result caching"
    )

    cache_ttl_days: int = Field(
        default=int(os.getenv("CACHE_TTL_DAYS", "7")),
        description="Cache time-to-live in days"
    )

    cache_dir: str = Field(
        default=os.getenv("CACHE_DIR", "./.cache/research"),
        description="Cache directory path"
    )

    # NEW: Logging Configuration
    log_level: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    structured_logging: bool = Field(
        default=os.getenv("STRUCTURED_LOGGING", "false").lower() == "true",
        description="Enable structured JSON logging"
    )

    log_file: Optional[str] = Field(
        default=os.getenv("LOG_FILE", None),
        description="Log file path (optional)"
    )

    # NEW: Advanced LLM Configuration
    llm_temperature: float = Field(
        default=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        description="LLM temperature for research"
    )

    synthesis_temperature: float = Field(
        default=float(os.getenv("SYNTHESIS_TEMPERATURE", "0.3")),
        description="LLM temperature for synthesis"
    )

    context_window_size: int = Field(
        default=int(os.getenv("CONTEXT_WINDOW_SIZE", "8192")),
        description="Context window size for local models"
    )

    enable_streaming: bool = Field(
        default=os.getenv("ENABLE_STREAMING", "false").lower() == "true",
        description="Enable content streaming"
    )

    max_tokens_per_call: int = Field(
        default=int(os.getenv("MAX_TOKENS_PER_CALL", "4096")),
        description="Maximum tokens per LLM call"
    )

    # NEW: Export Configuration
    enable_html_export: bool = Field(
        default=os.getenv("ENABLE_HTML_EXPORT", "true").lower() == "true",
        description="Enable HTML export"
    )

    enable_txt_export: bool = Field(
        default=os.getenv("ENABLE_TXT_EXPORT", "true").lower() == "true",
        description="Enable TXT export"
    )
    
    # LangSmith Configuration
    langsmith_tracing: bool = Field(
        default=os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true",
        description="Enable LangSmith tracing"
    )
    
    langsmith_project: str = Field(
        default=os.getenv("LANGCHAIN_PROJECT", "deep-research-agent"),
        description="LangSmith project name"
    )

    def __init__(self, **data):
        """Initialize and apply research mode defaults."""
        super().__init__(**data)
        self._apply_mode_defaults()
        self._parse_rss_config()

    def _apply_mode_defaults(self):
        """Apply research mode defaults if mode is set and fields aren't explicitly overridden."""
        mode = self.research_mode.lower()

        if mode not in RESEARCH_MODES:
            logger.warning(f"Unknown research mode '{mode}', using 'general'")
            mode = 'general'

        mode_config = RESEARCH_MODES[mode]

        # Apply mode defaults only if not explicitly set in env vars
        # Check if env vars were set (if they were, don't override with mode defaults)
        def apply_if_not_set(attr_name: str, mode_value: Any, env_var: str):
            """Apply mode default only if env var wasn't explicitly set."""
            if not os.getenv(env_var):
                setattr(self, attr_name, mode_value)

        apply_if_not_set('max_source_age_days', mode_config['max_source_age_days'], 'MAX_SOURCE_AGE_DAYS')
        apply_if_not_set('enable_deduplication', mode_config['enable_deduplication'], 'ENABLE_DEDUPLICATION')
        apply_if_not_set('deduplication_window_days', mode_config['deduplication_window_days'], 'DEDUPLICATION_WINDOW_DAYS')
        apply_if_not_set('enable_time_bound_searches', mode_config['enable_time_bound_searches'], 'ENABLE_TIME_BOUND_SEARCHES')
        apply_if_not_set('search_cache_ttl_hours', mode_config['search_cache_ttl_hours'], 'SEARCH_CACHE_TTL_HOURS')
        apply_if_not_set('enable_cloud_apis', mode_config['enable_cloud_apis'], 'ENABLE_CLOUD_APIS')
        apply_if_not_set('enable_recency_scoring', mode_config['enable_recency_scoring'], 'ENABLE_RECENCY_SCORING')
        apply_if_not_set('min_credibility_score', mode_config['min_credibility_score'], 'MIN_CREDIBILITY_SCORE')

        # Apply search API lists if not explicitly set
        if not os.getenv('PRIMARY_SEARCH_APIS') and not self.primary_search_apis:
            self.primary_search_apis = mode_config['primary_search_apis']
        if not os.getenv('FALLBACK_SEARCH_APIS') and not self.fallback_search_apis:
            self.fallback_search_apis = mode_config['fallback_search_apis']

        # Privacy mode enforcement
        if mode == 'privacy':
            if mode_config.get('force_local_models') and os.getenv('MODEL_PROVIDER') != 'ollama':
                logger.warning("Privacy mode requires local models - forcing MODEL_PROVIDER=ollama")
                self.model_provider = 'ollama'
            if mode_config.get('disable_api_search'):
                self.enable_reddit_search = False
                self.enable_hackernews_search = False  # If they require API keys

        logger.info(f"Research Mode: {mode.upper()} - {mode_config['description']}")

    def _parse_rss_config(self):
        """Parse RSS feed configuration from environment variables."""
        import json

        # Parse enabled RSS feeds from comma-separated string
        enabled_feeds_str = os.getenv("ENABLED_RSS_FEEDS")
        if enabled_feeds_str:
            self.enabled_rss_feeds = [feed.strip() for feed in enabled_feeds_str.split(",") if feed.strip()]

        # Parse disabled RSS feeds from comma-separated string
        disabled_feeds_str = os.getenv("DISABLED_RSS_FEEDS")
        if disabled_feeds_str:
            self.disabled_rss_feeds = [feed.strip() for feed in disabled_feeds_str.split(",") if feed.strip()]

        # Parse custom RSS feeds from JSON string
        if self.custom_rss_feeds:
            try:
                # Validate it's valid JSON
                custom_feeds = json.loads(self.custom_rss_feeds)
                if not isinstance(custom_feeds, dict):
                    logger.warning("CUSTOM_RSS_FEEDS must be a JSON object, ignoring")
                    self.custom_rss_feeds = None
                else:
                    # Validate feed structure
                    for feed_name, feed_config in custom_feeds.items():
                        if not isinstance(feed_config, dict):
                            logger.warning(f"Custom feed '{feed_name}' must be a dict, ignoring")
                            continue
                        if "url" not in feed_config:
                            logger.warning(f"Custom feed '{feed_name}' missing 'url', ignoring")
                            continue
                        # Set defaults for optional fields
                        feed_config.setdefault("description", feed_name)
                        feed_config.setdefault("priority", "medium")
                        feed_config.setdefault("max_items", 10)
                        feed_config.setdefault("require_keyword_match", False)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse CUSTOM_RSS_FEEDS: {e}, ignoring")
                self.custom_rss_feeds = None

    def validate_config(self) -> bool:
        """Validate that required configuration is present."""
        if self.model_provider == "gemini":
            if not self.google_api_key:
                raise ValueError(
                    "GEMINI_API_KEY is required when using Gemini. Get one from https://makersuite.google.com/app/apikey"
                )
        elif self.model_provider == "ollama":
            # Validate Ollama is accessible
            try:
                import requests
                response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                if response.status_code != 200:
                    raise ValueError(
                        f"Ollama server not accessible at {self.ollama_base_url}. "
                        f"Make sure Ollama is running: 'ollama serve'"
                    )
            except requests.exceptions.RequestException as e:
                raise ValueError(
                    f"Cannot connect to Ollama server at {self.ollama_base_url}. "
                    f"Error: {e}\n"
                    f"Make sure Ollama is installed and running: 'ollama serve'"
                )
        elif self.model_provider == "lmstudio":
            # Validate LM Studio is accessible
            try:
                import requests
                response = requests.get(f"{self.lmstudio_base_url}/models", timeout=5)
                if response.status_code != 200:
                    raise ValueError(
                        f"LM Studio server not accessible at {self.lmstudio_base_url}. "
                        f"Make sure LM Studio is running and the server is started."
                    )
            except requests.exceptions.RequestException as e:
                raise ValueError(
                    f"Cannot connect to LM Studio server at {self.lmstudio_base_url}. "
                    f"Error: {e}\n"
                    f"Make sure LM Studio is running with a model loaded and the local server is enabled."
                )
        elif self.model_provider == "openai":
            if not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required when using OpenAI. Get one from https://platform.openai.com/api-keys"
                )
        else:
            raise ValueError(
                f"Invalid MODEL_PROVIDER: {self.model_provider}. "
                f"Must be 'gemini', 'ollama', 'lmstudio', or 'openai'"
            )

        return True


# Global configuration instance
config = ResearchConfig()

# Log configuration for debugging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"Configuration loaded - MAX_SEARCH_QUERIES: {config.max_search_queries}, "
           f"MAX_SEARCH_RESULTS_PER_QUERY: {config.max_search_results_per_query}, "
           f"MAX_REPORT_SECTIONS: {config.max_report_sections}")

