# Changelog

## [2.0.0] - 2025-01-24

### Major Features Added

#### Three Operational Modes
- **WEEKLY MODE**: Recent news monitoring, 14-day filter, deduplication enabled
- **GENERAL MODE**: Comprehensive research, 365-day window, all sources
- **PRIVACY MODE**: Fully local, DuckDuckGo only, no external APIs

Set via `RESEARCH_MODE=weekly|general|privacy` in .env

#### Multi-Model Support with Lazy Loading
- **Lazy loading**: Models load only when agent runs, unload after completion
- **Memory efficient**: Run qwen3-next-80b + hermes-4-70b + mistral3-24b on 64GB RAM
- **Per-agent models**: Configure different models for each agent
  - `PLANNER_MODEL`: Planning agent (default: MODEL_NAME)
  - `SEARCH_MODEL`: Search agent (default: MODEL_NAME)
  - `SYNTHESIS_MODEL`: Synthesis agent (default: SUMMARIZATION_MODEL)
  - `WRITING_MODEL`: Writing agent (default: MODEL_NAME)

#### Premium Search APIs
- **Serper API**: Google Search for news, statistics, .gov sites
  - Authentication: `X-API-KEY` header
  - Date filtering: `tbs=qdr:d/w/m/y`
  - Best for: Recent news, authoritative sources

- **Tavily API**: Research-focused search for PDFs, reports
  - Authentication: `Authorization: Bearer {token}`
  - Advanced search depth
  - Best for: Academic papers, industry reports

- **Brave Search API**: General exploration with free tier
  - Authentication: `X-Subscription-Token` header
  - Freshness filtering: `pd/pw/pm/py`
  - Best for: General queries, fallback

- **MultiSearchClient Router**: Intelligent routing by query type
  - `news` → Serper (with weekly filter)
  - `research` → Tavily (advanced depth)
  - `statistics` → Serper (.gov prioritized)
  - `general` → Brave (free fallback)

#### Deduplication System
- Hash-based duplicate detection (URL + title)
- 30-day rolling window cache
- Automatic pruning of old entries
- Weekly mode only (prevents repeating sources)

#### Enhanced Source Filtering
- **Positive filtering**: Requires topic-relevant keywords in sources
- **Homepage detection**: Filters generic homepages (e.g., mckinsey.com/)
- **Citation verification**: Warns about potential citation mismatches
- **Unused reference removal**: Cleans bibliography automatically

### Technical Improvements

#### Workflow Optimization
- Model unloading between agent stages
- Wrapper functions for memory management
- Sequential execution: plan → unload → search → unload → synthesize → unload → write

#### Configuration Management
- Mode-based defaults with environment variable overrides
- Privacy mode enforcement (forces local models)
- API key validation and availability checking

### Configuration Changes

#### New Environment Variables
```bash
# Research Mode
RESEARCH_MODE=general  # weekly | general | privacy

# Search API Keys
SERPER_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
BRAVE_API_KEY=your_key_here

# Agent-Specific Models
PLANNER_MODEL=qwen3-next-80b
SEARCH_MODEL=hermes-4-70b
SYNTHESIS_MODEL=qwen3-next-80b
WRITING_MODEL=mistral3-24b

# Deduplication
ENABLE_DEDUPLICATION=true
DEDUPLICATION_WINDOW_DAYS=30

# Search Configuration
PRIMARY_SEARCH_APIS=serper,tavily
FALLBACK_SEARCH_APIS=brave,duckduckgo
SEARCH_CACHE_TTL_HOURS=24
ENABLE_CLOUD_APIS=true
```

### Migration Guide

#### From v1.x to v2.0

1. **Update .env file**:
   ```bash
   # Add research mode (optional - defaults to 'general')
   RESEARCH_MODE=general

   # Add search API keys if using premium APIs
   SERPER_API_KEY=your_key
   TAVILY_API_KEY=your_key
   ```

2. **Multi-model setup** (optional):
   ```bash
   # Example: Different models per agent
   PLANNER_MODEL=qwen3-next-80b
   SEARCH_MODEL=hermes-4-70b
   SYNTHESIS_MODEL=qwen3-next-80b
   WRITING_MODEL=mistral3-24b
   ```

3. **Weekly monitoring** (optional):
   ```bash
   RESEARCH_MODE=weekly
   SERPER_API_KEY=your_key  # Recommended for news
   ```

4. **Privacy mode** (optional):
   ```bash
   RESEARCH_MODE=privacy
   MODEL_PROVIDER=ollama  # Will be forced anyway
   ```

### Breaking Changes
- None - all changes are backward compatible

### Bug Fixes
- Citation integrity: Master source list prevents numbering mismatches
- Generic homepage filtering: No more placeholder citations
- Cross-competitor searches: Fixed "McKinsey report" on BCG sites
- Source relevance: Positive filtering eliminates off-topic papers

### Performance
- Memory usage: 85GB+ → <50GB (lazy loading)
- Search quality: Improved with premium APIs
- Deduplication: 15-30% reduction in repeated sources (weekly mode)

## [1.0.0] - Initial Release
- Multi-agent architecture with LangGraph
- Credibility scoring system
- Multiple export formats
- Ollama and Gemini support
