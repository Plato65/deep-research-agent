# Quality Controls & Observability Guide

Production-grade quality validation and observability system for ensuring report reliability.

## Overview

Deep Research Agent v2.1+ includes comprehensive quality controls to prevent bad reports from reaching production:

- **Self-Correction Loop**: Intelligent iterative refinement when quality is insufficient ⭐ NEW
- **Citation Verification**: Ensures all citations reference valid sources
- **Hallucination Detection**: Identifies unsupported claims without citations
- **Freshness Checking**: Verifies sources meet recency requirements
- **Observability**: Structured logging and telemetry for debugging
- **Pre-flight Validation**: Environment checks before research runs

## Self-Correction Loop ⭐ NEW

**The single biggest quality improvement** - enables iterative refinement when initial research is insufficient.

### How It Works

After synthesis, the **ResearchCritic agent** evaluates quality and decides whether to refine:

```
Plan → Search → Synthesize → Critique
                              ↓
                    Quality < 70? → YES → Search again (with feedback)
                              ↓             ↓
                             NO             Synthesize → Critique
                              ↓             ↓
                    Write Report ← Quality OK or Max Iterations
```

### ResearchCritic Agent

Evaluates synthesis quality on **5 dimensions**:

**1. Coverage (0-100)**: Do findings address ALL objectives?
- 100: All objectives fully addressed with comprehensive detail
- 75: Most objectives addressed, minor gaps
- 50: Some objectives addressed, significant gaps
- 25: Few objectives addressed
- 0: Objectives not addressed

**2. Evidence (0-100)**: Are claims well-supported by sources?
- 100: All findings backed by multiple quality sources
- 75: Most findings well-supported
- 50: Some findings lack evidence
- 25: Many unsupported claims
- 0: Little to no source backing

**3. Depth (0-100)**: Is analysis substantive or superficial?
- 100: Deep analysis with insights, context, implications
- 75: Good analysis with some depth
- 50: Basic facts with minimal analysis
- 25: Very superficial coverage
- 0: No meaningful analysis

**4. Specificity (0-100)**: Are findings concrete or vague?
- 100: Specific data, numbers, examples, names, dates
- 75: Mostly concrete with some specifics
- 50: Mix of specific and general statements
- 25: Mostly vague generalities
- 0: All generic statements

**5. Recency (0-100)**: Is information current and relevant?
- 100: Very recent information (< 30 days)
- 75: Recent information (< 6 months)
- 50: Somewhat dated (< 1 year)
- 25: Old information (> 1 year)
- 0: Outdated or no timestamps

**Overall Score**: Average of all 5 dimensions

### Refinement Logic

**If overall_score < 70 AND iterations < 2:**
1. Critic identifies **missing topics**
2. Critic provides **recommended queries** to address gaps
3. System loops back to **Search** with these specific queries
4. New sources gathered, synthesized, and re-evaluated

**Otherwise:**
- Proceed to report generation
- Quality acceptable OR max iterations reached

### Example Critique Output

```
✓ Research Critique
  Overall Score: 65/100

  Dimension Scores:
    Coverage: 60 (missing 2 of 5 objectives)
    Evidence: 70 (most claims supported)
    Depth: 55 (superficial in key areas)
    Specificity: 65 (lacks concrete data)
    Recency: 75 (mostly recent sources)

  Strengths:
    - Good source diversity
    - Recent information on market trends

  Weaknesses:
    - Missing analysis of regulatory impact
    - Lacks specific adoption numbers
    - Industry comparison superficial

  Missing Topics:
    - Regulatory framework changes
    - Adoption statistics by sector
    - Competitor analysis

  Recommended Queries:
    - "AI regulation impact 2024 specific rules"
    - "AI adoption statistics by industry 2024"
    - "competitive analysis AI platforms market share"

  Action: REFINE (iteration 1/2)
```

### Configuration

**Thresholds** (in `src/graph.py`):
```python
MAX_REFINEMENT_ITERATIONS = 2  # Maximum refinement loops
QUALITY_THRESHOLD = 70  # Minimum score to proceed
```

**Customize for your use case:**
```python
# Stricter quality (more iterations, higher threshold)
MAX_REFINEMENT_ITERATIONS = 3
QUALITY_THRESHOLD = 80

# Faster but lower quality (fewer iterations)
MAX_REFINEMENT_ITERATIONS = 1
QUALITY_THRESHOLD = 60
```

### When Self-Correction Triggers

**Common scenarios:**
1. **Insufficient coverage**: Initial search missed key objectives
2. **Lack of evidence**: Claims without source backing
3. **Superficial analysis**: Basic facts without depth
4. **Missing specifics**: Generic statements without data
5. **Outdated information**: Old sources for recent topics

**Example trigger:**
```
Research Topic: "Impact of GPT-4 on software development"

Initial Critique (Score: 62):
- Coverage: Missing "cost analysis" objective
- Evidence: Productivity claims lack source backing
- Specificity: No concrete adoption numbers

Action: Loop back to search with queries:
1. "GPT-4 cost comparison software development ROI"
2. "developer productivity GPT-4 statistics 2024"
3. "software company GPT-4 adoption rates"
```

### Benefits

**Quality improvements:**
- ✅ **Prevents incomplete research** - Catches missing objectives early
- ✅ **Ensures evidence backing** - No unsupported claims
- ✅ **Adds depth** - Surface-level findings trigger refinement
- ✅ **Demands specificity** - Generic analysis flagged for improvement
- ✅ **Maintains recency** - Old information triggers fresh search

**Cost efficiency:**
- ✅ **Targeted refinement** - Only searches for specific gaps
- ✅ **Early success exit** - Skips refinement if quality high
- ✅ **Limited iterations** - Max 2 loops prevents runaway cost

**Transparency:**
- ✅ **Detailed feedback** - Know exactly what's missing
- ✅ **Actionable queries** - See what additional searches will run
- ✅ **Iteration tracking** - Monitor refinement progress

### Telemetry

Self-correction events logged:

```json
{
  "event": "agent_completed",
  "agent": "critic",
  "duration_seconds": 2.1,
  "overall_score": 65,
  "should_refine": true,
  "timestamp": "2025-01-24T11:30:00"
}
```

**Monitor refinement frequency:**
```bash
cat outputs/telemetry/session_*.json | jq '.detailed_metrics.agents.critic.last_metrics.should_refine'
```

**Track quality scores over time:**
```bash
cat outputs/telemetry/session_*.json | jq '.detailed_metrics.agents.critic.last_metrics.overall_score'
```

## Quality Validation System

### Citation Verification

Validates that citations in the report reference actual sources in the bibliography.

**What it checks:**
- All citation numbers ([1], [2], etc.) reference valid source URLs
- No invalid citation numbers (e.g., [999] when only 50 sources exist)
- Sources in bibliography are actually cited in the report
- Citation coverage (% of sources that are cited)

**Example output:**
```
✓ Citation Verification
  Valid citations: 42/45 (93.3%)
  Invalid citations: []
  Uncited sources: 3
  Citation coverage: 93.3%
```

**Issues flagged:**
- Invalid citation numbers
- Low citation coverage (< 50%)
- Sources listed but never cited

### Hallucination Detection

Identifies sentences making factual claims without supporting citations.

**What it checks:**
- Sentences with claim indicators (research shows, data indicates, etc.)
- Absence of citations in factual claims
- Section-level citation density
- Overall hallucination risk (low/medium/high)

**Example output:**
```
✓ Hallucination Detection
  Unsupported claims: 2
  Sections below threshold: 0
  Hallucination risk: LOW
```

**Issues flagged:**
- Multiple unsupported claims (> 5)
- Sections with insufficient citations (< 2 per section)
- High hallucination risk

**What counts as a factual claim:**
- Statements with claim indicators:
  - "research shows", "study found", "data indicates"
  - Percentage/statistics: "40% of users", "$2.5 billion"
  - Time references: "in 2024", "increased by"
  - Definitive statements: "demonstrates that", "proves that"

**What doesn't count:**
- Questions
- Meta statements ("this section discusses", "we will examine")
- Introductory/conclusion paragraphs (less citation-heavy by nature)

### Freshness Checking

Verifies sources meet recency requirements based on research mode.

**What it checks:**
- Source dates extracted from URLs, titles, snippets
- Comparison against mode-specific thresholds
- Freshness score (% of sources within threshold)

**Mode-specific thresholds:**
- **Weekly mode**: 14 days (recent news monitoring)
- **General mode**: 365 days (comprehensive research)
- **Privacy mode**: 365 days (comprehensive research)

**Example output:**
```
✓ Freshness Check
  Recent sources: 18/25 (72%)
  Old sources: 7
  Freshness score: 72.0%
  Oldest date: 2024-01-15
```

**Issues flagged:**
- Insufficient recent sources (< min_recent_sources)
- Low freshness score (< 50%)
- More old sources than recent sources

### Overall Quality Score

Composite score combining all quality checks:

```
Overall Score = (
  Citation Coverage × 0.4 +
  Hallucination Score × 0.4 +
  Freshness Score × 0.2
)
```

**Scoring:**
- Citation coverage: 0-100% (from citation verification)
- Hallucination score: 100 (low), 50 (medium), 0 (high)
- Freshness score: 0-100% (from freshness check)

**Pass/Fail thresholds:**
- **Strict mode**: All checks must pass individually
- **Normal mode** (default): Overall score ≥ 60

**Example output:**
```
✓ Quality Validation: PASSED
  Overall score: 78.5/100
  Citation coverage: 93.3%
  Hallucination risk: LOW
  Freshness score: 72.0%
```

## Observability & Telemetry

### Structured Logging

All workflow events logged as structured JSON for monitoring/alerting.

**Log format:**
```json
{
  "event": "agent_completed",
  "agent": "searcher",
  "duration_seconds": 12.4,
  "sources_found": 25,
  "avg_credibility": 68.5,
  "dedup_filtered": 7,
  "api_used": "serper",
  "timestamp": "2025-01-24T10:30:45"
}
```

**Log events:**
- `agent_started`: Agent begins execution
- `agent_completed`: Agent finishes with metrics
- `search_completed`: Search operation with results
- `synthesis_completed`: Synthesis with findings count
- `quality_validation`: Validation results
- `model_operation`: Model load/unload events
- `error_occurred`: Error with structured context

### Per-Agent Telemetry

Each agent logs detailed metrics:

**Planner:**
- Duration
- Objectives count
- Search queries generated

**Searcher:**
- Duration
- Sources found
- Average credibility
- Duplicates filtered
- API used (Serper, Tavily, Brave, DuckDuckGo)

**Synthesizer:**
- Duration
- Findings extracted
- Sources used
- Average source credibility

**Writer:**
- Duration
- Report length
- Sections count

**Quality Validator:**
- Duration
- Passed/failed
- Overall score
- Individual check results

### Quality Alerts

Automatic alerts for quality degradation:

**Alert: Insufficient Sources**
- Trigger: < 5 sources found
- Severity: Medium
- Action: Check search API availability, query quality

**Alert: Low Credibility**
- Trigger: Average credibility < 50
- Severity: Medium
- Action: Review source filtering, check search queries

**Alert: Insufficient Findings**
- Trigger: < 3 key findings extracted
- Severity: High
- Action: Check synthesis prompt, verify source quality

**Alert: Quality Validation Failed**
- Trigger: Overall score < 60 (or any check fails in strict mode)
- Severity: Critical
- Action: Review report before publishing

### Session Metrics

Comprehensive metrics saved after each research run:

**Location:** `outputs/telemetry/session_YYYYMMDD_HHMMSS.json`

**Contents:**
```json
{
  "summary": {
    "session_id": "20250124_103045",
    "duration_seconds": 45.2,
    "agents": {
      "planner": {"executions": 1, "total_duration": 3.2},
      "searcher": {"executions": 1, "total_duration": 18.5},
      "synthesizer": {"executions": 1, "total_duration": 12.1},
      "writer": {"executions": 1, "total_duration": 9.8},
      "quality_validator": {"executions": 1, "total_duration": 1.6}
    },
    "quality_alerts_count": 0,
    "errors_count": 0
  },
  "detailed_metrics": {
    "agents": { ... },
    "quality_alerts": [],
    "errors": []
  }
}
```

**Usage:**
- Performance optimization: Identify slow agents
- Quality tracking: Monitor alert frequency over time
- Debugging: Review detailed metrics for failed runs
- Cost analysis: Track duration and token usage

## Pre-Flight Validation

Environment checks before research runs to catch configuration issues early.

### Checks Performed

**1. Basic Configuration**
- Model provider connectivity (Gemini, OpenAI, Ollama, LM Studio)
- API keys present and valid
- Research mode configuration

**2. Search APIs**
- Serper API: Test connectivity with dummy query
- Tavily API: Verify authentication
- Brave API: Check subscription token
- Fallback: Warn if no premium APIs configured

**3. Cache Directories**
- `./.cache/research` - Research result cache
- `./.cache/deduplication` - Deduplication hashes
- `./outputs` - Report output directory
- `./outputs/telemetry` - Telemetry metrics

**4. Cost Estimation**
- Gemini: ~$0.0034 per report
- OpenAI: ~$0.0064 per report
- Ollama/LM Studio: Free (local models)

**5. Model Configuration**
- Display multi-model setup if configured
- Show default model if single-model mode

### Validation Output

```
================================================================================
PRE-FLIGHT ENVIRONMENT VALIDATION
================================================================================

✓ PASS       | Basic Configuration       | Provider: gemini, Mode: weekly
TESTED       | Search APIs               | Serper: ✓, Tavily: ✓, Brave: ✗ (HTTP 401)
✓ PASS       | Cache Directories         | All 4 directories accessible
INFO         | Cost Estimate             | ~$0.0034 per report (Gemini)
ENABLED      | Multi-Model Setup         | Planner: qwen3-next-80b, Search: hermes-4-70b

⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠
WARNINGS:
  ⚠ Brave API returned status 401
⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠⚠

================================================================================
✓ VALIDATION PASSED - Ready to start research
================================================================================
```

**Failure scenarios:**
- Missing API keys (for required providers)
- Ollama/LM Studio not running
- Cache directories not writable
- No search APIs available (in weekly/general mode)

## Configuration

### Quality Validation Settings

Quality validation is **enabled by default** and runs automatically after report generation.

**Disable validation** (not recommended for production):
```python
# In src/graph.py, comment out quality validation node
# workflow.add_node("validate_quality", validate_quality)
```

**Adjust thresholds:**
```python
# In src/utils/quality_checks.py
validation_results = await quality_validator.validate_report(
    report=state.final_report,
    sources=state.search_results,
    mode=config.research_mode,
    strict=True  # Require all checks to pass individually
)
```

### Telemetry Settings

Telemetry is **enabled by default** and saved automatically.

**Output directory:**
```bash
# Default: ./outputs/telemetry
# Configure via TelemetryTracker initialization
telemetry = TelemetryTracker(output_dir="./custom/path")
```

**Disable telemetry** (not recommended):
```python
# In src/graph.py, remove telemetry calls
# telemetry = get_telemetry()  # Comment this out
```

### Alert Thresholds

Customize alert thresholds in `src/utils/telemetry.py`:

```python
# Insufficient sources alert
if len(sources) < 5:  # Change threshold here
    self.alert_insufficient_sources(query, len(sources))

# Low credibility alert
if avg_credibility < 50:  # Change threshold here
    self.alert_low_credibility(query, avg_credibility)

# Insufficient findings alert
if count < 3:  # Change threshold here
    self.alert_insufficient_findings(count)
```

## Usage Examples

### Running with Validation

Validation runs automatically:

```bash
python main.py "Recent AI developments"
```

**Output includes:**
```
INFO: Quality validation: PASSED
INFO:   Overall score: 78.5/100
INFO:   Citation coverage: 93.3%
INFO:   Hallucination risk: low
INFO:   Freshness score: 72.0%
INFO: Session summary:
INFO:   Duration: 45.2s
INFO:   Quality alerts: 0
INFO:   Errors: 0
INFO: Telemetry metrics saved
```

### Reviewing Telemetry

Check session metrics:

```bash
cat outputs/telemetry/session_20250124_103045.json | jq .
```

**Find slow agents:**
```bash
cat outputs/telemetry/session_*.json | jq '.summary.agents | to_entries | sort_by(.value.total_duration) | reverse'
```

**Count quality alerts:**
```bash
cat outputs/telemetry/session_*.json | jq '.summary.quality_alerts_count'
```

### Debugging Failed Validation

If quality validation fails:

1. **Check citation issues:**
   ```
   Quality issues:
     - Invalid citations found: [52, 53]
     - Low citation coverage: 42.0%
   ```
   Action: Review report generation, ensure citations match sources

2. **Check hallucination issues:**
   ```
   Quality issues:
     - 8 sentences with unsupported claims
     - 2 sections below citation threshold
   ```
   Action: Review synthesis prompt, ensure claims are cited

3. **Check freshness issues:**
   ```
   Quality issues:
     - Only 2 recent sources (need 5)
     - Low freshness score: 35.0%
   ```
   Action: Check research mode (weekly vs general), verify search APIs

## Best Practices

### For Production Weekly Reports

1. **Enable strict validation:**
   ```python
   strict=True  # Require all checks to pass
   ```

2. **Monitor telemetry:**
   - Review session metrics after each run
   - Track quality alert frequency
   - Alert on repeated failures

3. **Set appropriate thresholds:**
   - Weekly mode: Require higher freshness (14 days)
   - Increase min_recent_sources for weekly monitoring

4. **Review validation failures:**
   - Never publish reports that fail validation
   - Investigate root cause before re-running

### For Development/Testing

1. **Use normal mode:**
   ```python
   strict=False  # Allow passes with overall score ≥ 60
   ```

2. **Experiment with thresholds:**
   - Adjust alert thresholds for your use case
   - Test with different research modes

3. **Review detailed metrics:**
   - Check per-agent performance
   - Identify bottlenecks
   - Optimize prompts based on metrics

### For Privacy Mode

1. **Validation still works:**
   - All quality checks run with local models
   - No external API calls for validation

2. **Adjust expectations:**
   - DuckDuckGo may have lower source quality
   - Freshness checking may find fewer dates
   - Consider lowering thresholds slightly

## Troubleshooting

### "No report to validate" warning

**Cause:** Report generation failed before validation
**Fix:** Check earlier logs for synthesis/writing errors

### High false positive rate for hallucinations

**Cause:** Claim detection too sensitive
**Fix:** Adjust `_is_factual_claim()` indicators in quality_checks.py

### Freshness score always 50%

**Cause:** Can't extract dates from sources
**Fix:** Improve date extraction in `_extract_date()` method

### Telemetry file not saved

**Cause:** Permissions issue or invalid path
**Fix:** Check `outputs/telemetry/` directory exists and is writable

### Validation taking too long

**Cause:** Large report with many sources
**Fix:** Validation is fast (<2s typically), check for other bottlenecks

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Research Quality Check

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9am

jobs:
  weekly-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run research
        run: |
          python main.py "Weekly AI developments"

      - name: Check validation
        run: |
          # Parse telemetry for validation results
          score=$(jq '.detailed_metrics.agents.quality_validator.last_metrics.overall_score' outputs/telemetry/session_*.json)
          if (( $(echo "$score < 60" | bc -l) )); then
            echo "Quality validation failed: score=$score"
            exit 1
          fi

      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: weekly-report
          path: outputs/*.md
```

## Next Steps

With quality controls in place, the next phase implements:

1. **Self-Correction Loop** (Week 2-3)
   - ResearchCritic agent evaluates synthesis quality
   - Conditional routing back to search based on validation
   - Iterative refinement for insufficient results

2. **Automated Testing** (Week 3-4)
   - Golden dataset regression tests
   - Quality threshold assertions
   - Integration tests for validation system

3. **Advanced Monitoring** (Week 4+)
   - Real-time dashboards for metrics
   - Alert routing to Slack/email
   - Trend analysis over time

Quality controls provide the foundation for reliable production operation.
