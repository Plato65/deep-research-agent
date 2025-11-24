# Research Modes Guide

Deep Research Agent supports three operational modes optimized for different use cases.

## Quick Comparison

| Feature | Weekly | General | Privacy |
|---------|--------|---------|---------|
| **Date Filter** | 14 days | 365 days | 365 days |
| **Deduplication** | ✅ Enabled | ❌ Disabled | ❌ Disabled |
| **Search APIs** | Serper + Tavily | All APIs | DuckDuckGo only |
| **Cache TTL** | 6 hours | 24 hours | 24 hours |
| **Cloud APIs** | ✅ Enabled | ✅ Enabled | ❌ Disabled |
| **Model Provider** | Any | Any | Ollama (forced) |

## Weekly Mode

**Best for**: News monitoring, tracking recent developments, weekly briefings

### Configuration
```bash
RESEARCH_MODE=weekly
SERPER_API_KEY=your_key  # Recommended
TAVILY_API_KEY=your_key  # Recommended
```

### Behavior
- **Date filter**: Only sources from last 14 days
- **Deduplication**: Enabled with 30-day window
  - Tracks previously reported sources
  - Filters duplicates automatically
  - Saves hashes after each report
- **Search APIs**: Prioritizes Serper (news) and Tavily (research)
- **Cache TTL**: 6 hours (fresher results)
- **Time-bound searches**: Adds "2024", "latest", "recent" to queries

### Use Cases
- Weekly AI/tech news briefings
- Market monitoring reports
- Regulatory update tracking
- Competitive intelligence monitoring

### Example Output
```
INFO: Research Mode: WEEKLY - Weekly monitoring: recent news (<14 days), deduplication, fast updates
INFO: Loaded 127 previous source hashes from last 30 days
INFO: Deduplication: 18 new, 7 duplicates (28.0%)
INFO: Filtered 25 -> 18 results (dedup_filtered=7)
```

## General Mode

**Best for**: Comprehensive research, deep dives, academic work

### Configuration
```bash
RESEARCH_MODE=general  # Default
SERPER_API_KEY=your_key  # Optional
TAVILY_API_KEY=your_key  # Optional
BRAVE_API_KEY=your_key   # Optional
```

### Behavior
- **Date filter**: 365 days (essentially unlimited)
- **Deduplication**: Disabled
- **Search APIs**: Uses all available (Serper, Tavily, Brave, DuckDuckGo)
- **Cache TTL**: 24 hours
- **Time-bound searches**: Disabled

### Use Cases
- Academic literature reviews
- Market research reports
- Technology trend analysis
- Historical research

### Example Output
```
INFO: Research Mode: GENERAL - General research: comprehensive, no date limits, all sources
INFO: Search APIs available: serper, tavily, brave, duckduckgo
INFO: Filtered 30 -> 25 results (min_credibility=40, age_filtered=0, relevance_filtered=5)
```

## Privacy Mode

**Best for**: Sensitive research, air-gapped environments, no tracking

### Configuration
```bash
RESEARCH_MODE=privacy
MODEL_PROVIDER=ollama  # Will be forced
```

### Behavior
- **Date filter**: 365 days
- **Deduplication**: Disabled
- **Search APIs**: DuckDuckGo only (no API keys required)
- **Cloud APIs**: Disabled
- **Model provider**: Forced to Ollama (local models only)
- **Specialized search**: ArXiv only (no Reddit/HN requiring API keys)

### Use Cases
- Confidential business intelligence
- Legal research (attorney-client privilege)
- Medical research (HIPAA compliance)
- Government/defense research
- Air-gapped networks

### Example Output
```
INFO: Research Mode: PRIVACY - Privacy mode: local models, no external APIs, no tracking
WARNING: Privacy mode requires local models - forcing MODEL_PROVIDER=ollama
INFO: Search APIs: DuckDuckGo only (no API keys)
INFO: No external tracking or API calls
```

## Mode Overrides

You can override specific settings per mode:

```bash
RESEARCH_MODE=weekly

# Override date filter
MAX_SOURCE_AGE_DAYS=7  # Instead of default 14

# Override deduplication window
DEDUPLICATION_WINDOW_DAYS=60  # Instead of default 30

# Override search APIs
PRIMARY_SEARCH_APIS=brave,duckduckgo  # No premium APIs
```

## Switching Modes

Simply change `RESEARCH_MODE` in your .env file:

```bash
# Monday: Weekly briefing
RESEARCH_MODE=weekly

# Tuesday: Deep research
RESEARCH_MODE=general

# Wednesday: Sensitive topic
RESEARCH_MODE=privacy
```

No code changes required - mode configurations apply automatically.

## Best Practices

### Weekly Mode
- Run on a schedule (cron, GitHub Actions)
- Archive reports with timestamps
- Monitor deduplication stats
- Use premium search APIs for quality

### General Mode
- Allocate more time for comprehensive search
- Review credibility scores
- Consider cost of premium APIs
- Cache results for reuse

### Privacy Mode
- Verify no outbound connections
- Use local models exclusively
- Check .cache/ directory is local
- Review logs for any API calls
