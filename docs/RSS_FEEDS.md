# RSS/Newsletter Ingestion

**Early Signal Detection with RSS/Atom Feeds**

The Deep Research Agent includes powerful RSS/Atom feed ingestion capabilities to detect signals before they're indexed by search engines. This is particularly valuable for monitoring AI/ML research, blog posts, and paper releases.

---

## Table of Contents

- [Overview](#overview)
- [Built-in Feeds](#built-in-feeds)
- [Per-Feed Configuration](#per-feed-configuration)
- [High-Volume Feed Handling](#high-volume-feed-handling)
- [Feed Selection](#feed-selection)
- [Custom Feeds](#custom-feeds)
- [Configuration Reference](#configuration-reference)
- [Examples](#examples)

---

## Overview

RSS feed ingestion provides several advantages:

1. **Early Signal Detection**: Catch new research papers, blog posts, and announcements before Google indexes them
2. **Authoritative Sources**: Direct access to official blogs from OpenAI, Anthropic, Meta, Google, etc.
3. **Research Papers**: Monitor arXiv categories (CS.AI, CS.LG, CS.CL) for relevant papers
4. **Smart Filtering**: Keyword-based relevance filtering for high-volume feeds
5. **Credibility Scoring**: RSS items go through the same credibility evaluation as web search results

---

## Built-in Feeds

The agent includes 13 pre-configured feeds across four categories:

### Official Blogs (High Priority)
- **OpenAI Blog** - Official OpenAI announcements and research
- **Anthropic News** - Anthropic news and research updates
- **Google AI Blog** - Google's AI research and products
- **Meta AI Blog** - Meta's AI research and developments
- **DeepMind Blog** - Google DeepMind's research blog
- **Hugging Face Blog** - Community hub for ML/NLP

### Research Papers (Medium Priority)
- **arXiv CS.AI** - Artificial Intelligence papers (~150/day)
- **arXiv CS.LG** - Machine Learning papers (~200/day)
- **arXiv CS.CL** - Computation and Language papers (~100/day)
- **Papers with Code** - Latest papers with implementations

### Industry News (Medium/Low Priority)
- **MIT Technology Review AI** - AI technology journalism
- **VentureBeat AI** - AI business and industry news

---

## Per-Feed Configuration

Each feed has individual configuration for optimal performance:

```python
"arxiv_cs_ai": {
    "url": "http://export.arxiv.org/rss/cs.AI",
    "description": "arXiv CS.AI (Artificial Intelligence)",
    "priority": "medium",
    "max_items": 200,              # Fetch up to 200 items
    "require_keyword_match": True,  # MUST match topic keywords
    "return_top_n": 5              # Return only top 5 after filtering
}
```

### Configuration Fields

- **url** (required): RSS/Atom feed URL
- **description** (required): Human-readable description
- **priority** (required): "high", "medium", or "low"
- **max_items** (optional, default: 10): Maximum items to fetch from feed
- **require_keyword_match** (optional, default: False): Whether to require keyword matching
- **return_top_n** (optional, default: None): Limit to top N after relevance filtering

---

## High-Volume Feed Handling

For feeds like arXiv that publish 100+ items per day, the agent uses a smart filtering approach:

### The Challenge

arXiv CS.AI publishes ~150 papers/day. Over 7 days, that's 1050+ papers. We can't process them all.

### The Solution

**Fetch → Filter → Rank → Limit**

1. **Fetch**: Retrieve up to `max_items` most recent entries (e.g., 200 items = ~1.3 days)
2. **Filter**: Apply keyword matching to identify relevant papers
3. **Rank**: Score matches by relevance (title matches score higher)
4. **Limit**: Return only top N most relevant items

### Example: arXiv Filtering

Research topic: "transformer models for language understanding"

```
Fetched: 200 most recent arXiv CS.AI papers
Keywords: ["transformer", "models", "language", "understanding"]

Filtering:
  - Paper 1: "Attention is All You Need" → matches "transformer" (title) → score: 2.0
  - Paper 2: "BERT: Pre-training of Deep Bidirectional Transformers" → matches "transformer", "language" → score: 4.0
  - Paper 3: "Quantum Computing Applications" → no match → filtered out

After ranking: 47 relevant papers
After limiting (top 5): 5 most relevant papers returned
```

### Configuration Strategy

**Low-Volume Feeds** (Official blogs, ~10 posts/month):
```python
"max_items": 10,
"require_keyword_match": False  # Trust all items from authoritative source
```

**High-Volume Feeds** (arXiv, ~150 papers/day):
```python
"max_items": 200,               # Fetch more to cover 1-2 days
"require_keyword_match": True,  # Filter by topic relevance
"return_top_n": 5              # Return only top 5 matches
```

---

## Feed Selection

Control which feeds are used for your research:

### Enable All Feeds (Default)

```bash
ENABLE_RSS_FEEDS=true
```

### Enable Specific Feeds Only

```bash
# Only fetch from OpenAI, Anthropic, and arXiv AI
ENABLED_RSS_FEEDS="openai_blog,anthropic_blog,arxiv_cs_ai"
```

When `ENABLED_RSS_FEEDS` is set, ONLY those feeds will be fetched (ignoring priority filter).

### Disable Specific Feeds

```bash
# Disable industry news feeds
DISABLED_RSS_FEEDS="venturebeat_ai,mit_tech_ai"
```

Disabled feeds are excluded even if they match other filters.

### Filter by Priority

```bash
# Only fetch high-priority feeds (official blogs)
RSS_PRIORITY_FILTER="high"
```

Priority levels:
- **high**: Official company blogs, authoritative sources
- **medium**: Research papers, community hubs
- **low**: Industry news, aggregators

---

## Custom Feeds

Add your own RSS/Atom feeds:

### Environment Variable

```bash
CUSTOM_RSS_FEEDS='{
  "my_research_blog": {
    "url": "https://example.com/research/feed.xml",
    "description": "My Research Blog",
    "priority": "high",
    "max_items": 15,
    "require_keyword_match": false
  },
  "specialized_arxiv": {
    "url": "http://export.arxiv.org/rss/cs.CV",
    "description": "arXiv Computer Vision",
    "priority": "medium",
    "max_items": 100,
    "require_keyword_match": true,
    "return_top_n": 3
  }
}'
```

### Required Fields

- **url**: RSS/Atom feed URL
- **description**: Human-readable description

### Optional Fields (with defaults)

- **priority**: "medium"
- **max_items**: 10
- **require_keyword_match**: false
- **return_top_n**: None (no limit after filtering)

---

## Configuration Reference

### Basic Settings

```bash
# Enable RSS feed ingestion (default: true)
ENABLE_RSS_FEEDS=true

# How many days back to fetch (default: 7)
RSS_FEED_DAYS=7

# Maximum items per feed (deprecated, use per-feed config)
RSS_MAX_ITEMS_PER_FEED=10

# Priority filter (default: None = all priorities)
RSS_PRIORITY_FILTER="high"
```

### Feed Selection

```bash
# Enable only specific feeds (default: None = all)
ENABLED_RSS_FEEDS="openai_blog,anthropic_blog,arxiv_cs_ai"

# Disable specific feeds (default: empty)
DISABLED_RSS_FEEDS="venturebeat_ai,mit_tech_ai"

# Add custom feeds (default: None)
CUSTOM_RSS_FEEDS='{"my_feed": {...}}'
```

---

## Examples

### Example 1: Only Official Blogs

Focus on high-signal, low-volume authoritative sources:

```bash
RSS_PRIORITY_FILTER="high"
RSS_FEED_DAYS=14  # Look back 2 weeks
```

This fetches from:
- OpenAI Blog
- Anthropic News
- Google AI Blog
- Meta AI Blog
- DeepMind Blog
- Hugging Face Blog

### Example 2: arXiv Papers Only

Monitor research papers with smart filtering:

```bash
ENABLED_RSS_FEEDS="arxiv_cs_ai,arxiv_cs_lg,arxiv_cs_cl"
RSS_FEED_DAYS=3  # Recent papers only
```

For topic "vision transformers", this will:
1. Fetch 200 most recent papers from each feed (~600 total)
2. Filter by keywords: ["vision", "transformers"]
3. Rank by relevance (title matches score higher)
4. Return top 5 from each feed (15 total)

### Example 3: Custom Research Monitoring

Add a specialized blog and exclude industry news:

```bash
DISABLED_RSS_FEEDS="venturebeat_ai,mit_tech_ai"

CUSTOM_RSS_FEEDS='{
  "distill_pub": {
    "url": "https://distill.pub/rss.xml",
    "description": "Distill Research",
    "priority": "high",
    "require_keyword_match": false
  }
}'
```

### Example 4: Maximum Coverage

Fetch from all sources for comprehensive research:

```bash
ENABLE_RSS_FEEDS=true
RSS_FEED_DAYS=7
# No priority filter, no enabled/disabled lists
```

This uses all 13 built-in feeds with smart filtering for high-volume sources.

---

## How RSS Integration Works

### 1. Feed Fetching

When research begins, the agent:

1. Initializes RSSFeedReader with your configuration
2. Filters feeds by enabled/disabled lists and priority
3. Fetches feeds concurrently (async for speed)
4. Parses entries with `feedparser`

### 2. Smart Filtering

For each feed:

1. Fetch up to `max_items` most recent entries
2. Filter by publication date (within `RSS_FEED_DAYS`)
3. If `require_keyword_match=True`:
   - Extract keywords from research topic
   - Match against title and snippet
   - Calculate relevance score (title matches = 2x weight)
   - Sort by relevance
4. If `return_top_n` is set, limit to top N
5. Convert to SearchResult format

### 3. Credibility Evaluation

RSS results go through the same credibility scoring as web results:

- **Source Authority**: Official blogs score highest
- **Content Quality**: Checked for depth and evidence
- **Recency**: Recent items score higher
- **Relevance**: Keyword matching boosts score

### 4. Integration with Search

RSS results are merged with web search results:

1. RSS items are added at the beginning (most recent)
2. Combined with web search results
3. Deduplicated by URL
4. Filtered by credibility threshold
5. Passed to synthesis agent

---

## Best Practices

### 1. Start with High Priority

For most research, official blogs provide the highest signal:

```bash
RSS_PRIORITY_FILTER="high"
```

### 2. Use arXiv Strategically

arXiv feeds are high-volume. Use them for deep technical research:

```bash
# For AI safety research
ENABLED_RSS_FEEDS="arxiv_cs_ai,arxiv_cs_lg"
```

### 3. Adjust Lookback Period

- **Breaking news**: `RSS_FEED_DAYS=1` (last 24 hours)
- **Weekly updates**: `RSS_FEED_DAYS=7` (default)
- **Historical research**: `RSS_FEED_DAYS=30` (last month)

### 4. Combine with Search Modes

RSS works great with research modes:

```bash
# Fast mode with RSS for breaking news
RESEARCH_MODE="fast"
RSS_PRIORITY_FILTER="high"
RSS_FEED_DAYS=3

# Deep mode with arXiv for comprehensive research
RESEARCH_MODE="deep"
ENABLED_RSS_FEEDS="arxiv_cs_ai,arxiv_cs_lg,arxiv_cs_cl"
RSS_FEED_DAYS=7
```

### 5. Monitor Custom Sources

Add feeds from your favorite researchers or organizations:

```bash
CUSTOM_RSS_FEEDS='{
  "colah_blog": {
    "url": "https://colah.github.io/rss.xml",
    "description": "Christopher Olah Blog",
    "priority": "high"
  }
}'
```

---

## Troubleshooting

### No RSS Results

**Check if RSS is enabled:**
```bash
ENABLE_RSS_FEEDS=true
```

**Check feed selection:**
```bash
# Are you filtering too aggressively?
ENABLED_RSS_FEEDS=""  # Clear to use all feeds
```

**Check lookback period:**
```bash
RSS_FEED_DAYS=14  # Increase if feeds are low-volume
```

### Too Many RSS Results

**Use priority filter:**
```bash
RSS_PRIORITY_FILTER="high"
```

**Limit to specific feeds:**
```bash
ENABLED_RSS_FEEDS="openai_blog,anthropic_blog"
```

**Reduce lookback:**
```bash
RSS_FEED_DAYS=3
```

### arXiv Returns Irrelevant Papers

The keyword matching is basic. Improve by:

1. **More specific research topics**: "vision transformers for object detection" vs. "transformers"
2. **Use fewer feeds**: Focus on most relevant arXiv category
3. **Adjust return_top_n**: Lower for higher precision

### Custom Feed Not Working

**Check JSON syntax:**
```bash
# Test JSON validity
echo $CUSTOM_RSS_FEEDS | python3 -m json.tool
```

**Check required fields:**
- url (required)
- description (optional but recommended)

**Check logs:**
```bash
# Look for "Adding N custom RSS feeds"
# Look for "Custom feed 'X' missing 'url', ignoring"
```

---

## Advanced Configuration

### Per-Feed Defaults in Code

You can modify default feeds in `src/utils/rss_reader.py`:

```python
FEEDS = {
    "openai_blog": {
        "url": "https://openai.com/blog/rss.xml",
        "description": "OpenAI official blog",
        "priority": "high",
        "max_items": 10,
        "require_keyword_match": False
    },
    # Add more feeds...
}
```

### Custom Relevance Scoring

Modify `_calculate_relevance_score()` in `RSSFeedReader`:

```python
def _calculate_relevance_score(self, item: SearchResult, keywords: set) -> float:
    score = 0.0
    title_lower = item.title.lower()
    snippet_lower = item.snippet.lower()

    # Customize scoring weights
    for keyword in keywords:
        if keyword in title_lower:
            score += 3.0  # Increase title weight
        if keyword in snippet_lower:
            score += 1.0

    return score
```

---

## Future Enhancements

Planned improvements:

1. **Semantic Matching**: Use embeddings for better relevance than keyword matching
2. **Feed Discovery**: Auto-discover RSS feeds from websites
3. **Newsletter Email**: Parse newsletter emails (Substack, etc.)
4. **Feed Health Monitoring**: Track feed uptime and freshness
5. **Personalized Feed Ranking**: Learn from user preferences

---

## See Also

- [Research Modes](MODES.md) - How RSS integrates with research modes
- [Quality Controls](QUALITY_CONTROLS.md) - How RSS results are evaluated
- [Multi-Model Setup](MULTI_MODEL_SETUP.md) - Model configuration for RSS processing

---

**Questions or Issues?**

RSS feed ingestion is a powerful feature for early signal detection. If you have questions or encounter issues, please open an issue on GitHub.
