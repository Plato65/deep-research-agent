# Deep Research Agent - Configuration Guide

**Complete guide to configuring models for each workflow stage**

---

## Table of Contents

- [Overview](#overview)
- [Workflow Stages Explained](#workflow-stages-explained)
- [Configuration Strategies](#configuration-strategies)
- [Your Recommended Setup](#your-recommended-setup)
- [Configuration Examples](#configuration-examples)
- [Model Selection Guide](#model-selection-guide)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Deep Research Agent runs through 5 sequential stages. You can use **different models for each stage** to optimize for quality, speed, and cost.

### The 5 Workflow Stages

```
┌─────────────┐
│ 1. PLANNING │ → Generate research objectives & search queries
└─────────────┘
      ↓
┌─────────────┐
│ 2. SEARCHING│ → Execute searches via APIs, generate more queries
└─────────────┘
      ↓
┌─────────────┐
│ 3. SYNTHESIS│ → Extract key findings from search results
└─────────────┘
      ↓
┌─────────────┐
│ 4. CRITIQUE │ → Evaluate quality (optional self-correction loop)
└─────────────┘
      ↓
┌─────────────┐
│ 5. WRITING  │ → Generate final report with citations
└─────────────┘
```

---

## Workflow Stages Explained

### Stage 1: Planning (ResearchPlanner)

**What it does:**
- Analyzes your research topic
- Generates 3-5 research objectives
- Creates 5+ search queries to find relevant information

**Model Requirements:**
- **Reasoning ability**: Good logical thinking to create comprehensive objectives
- **Speed**: Not critical (runs once per research task)
- **Cost**: Low impact (short prompts, ~500 tokens output)

**Best Models:**
- **Premium**: GPT-4o, Gemini 2.0 Pro, OLMo 3 32B Think
- **Balanced**: Gemini 2.5 Flash, GPT-4o Mini
- **Local**: Qwen 2.5 7B, Llama 3.1 8B

**Configuration:**
```bash
PLANNER_MODEL=gemini-2.5-flash  # Cloud
# OR
PLANNER_MODEL=local-model  # LM Studio with Olmo-3-32B-Think
```

---

### Stage 2: Searching (ResearchSearcher)

**What it does:**
- Executes search queries via APIs (Serper, Tavily, DuckDuckGo)
- Scrapes content from top results
- Generates follow-up queries if needed
- Assesses source credibility

**Model Requirements:**
- **Query generation**: Moderate reasoning for follow-up queries
- **Speed**: Important (runs 5+ searches with retries)
- **Cost**: Moderate impact (5-10 LLM calls per research)

**Best Models:**
- **Premium**: Gemini 2.5 Flash (fast + smart)
- **Balanced**: GPT-4o Mini, Qwen 2.5 7B
- **Local**: Qwen 2.5 7B, Llama 3.1 8B

**Configuration:**
```bash
SEARCH_MODEL=gemini-2.5-flash  # Cloud (recommended)
# OR
SEARCH_MODEL=local-model  # LM Studio
```

**Note:** DR Tulu is NOT recommended for this stage (it's optimized for writing, not query generation)

---

### Stage 3: Synthesis (ResearchSynthesizer)

**What it does:**
- Reads all search results
- Extracts key findings (10-20 bullet points)
- Prioritizes high-credibility sources
- Identifies contradictions and debates

**Model Requirements:**
- **Summarization**: Strong ability to distill information
- **Speed**: Important (processes 20+ sources)
- **Cost**: High impact (largest input: ~10,000 tokens)

**Best Models:**
- **Premium**: Gemini 2.5 Flash (excellent summarization)
- **Balanced**: GPT-4o Mini, Qwen 2.5 7B
- **Local**: Qwen 2.5 7B, Llama 3.1 8B

**Configuration:**
```bash
SYNTHESIS_MODEL=gemini-2.5-flash  # Cloud (recommended)
# OR
SYNTHESIS_MODEL=local-model  # LM Studio
```

---

### Stage 4: Critique (ResearchCritic / OLMoThinker)

**What it does:**
- Evaluates research quality on 5 dimensions:
  - Coverage (do findings address all objectives?)
  - Evidence (are claims well-supported?)
  - Depth (is analysis substantive?)
  - Specificity (concrete vs vague?)
  - Recency (is information current?)
- Provides feedback for improvement
- Triggers refinement loop if quality < 70/100

**Model Requirements:**
- **Reasoning**: CRITICAL - needs to evaluate quality objectively
- **Speed**: Moderate (runs 1-2 times per research)
- **Cost**: Moderate impact (~2,000 tokens input/output)

**Best Models:**
- **Premium**: **OLMo 3 32B Think** (explicit reasoning with `<think>` tags)
- **Alternative**: GPT-4o, Gemini 2.0 Pro
- **Balanced**: Gemini 2.5 Flash, GPT-4o Mini

**Configuration:**
```bash
# Recommended: Use OLMo via LM Studio
USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1234/v1

# Alternative: Use main model
USE_OLMO_CRITIC=false
```

**Why OLMo 3 32B Think?**
- Explicit `<think>` tags show reasoning process
- Strong analytical performance (89.8 BigBenchHard, 96.1 MATH)
- Better gap detection than standard models

---

### Stage 5: Writing (ReportWriter / DRTuluReportWriter)

**What it does:**
- Writes each report section based on findings
- Inserts citations for every factual claim
- Compiles sections into final report
- Formats references in chosen style (APA, MLA, etc.)

**Model Requirements:**
- **Citation accuracy**: CRITICAL - must map citations correctly
- **Writing quality**: Important - clear, academic prose
- **Speed**: Less critical (runs once, ~5-10 sections)
- **Cost**: High impact (largest output: ~5,000 tokens)

**Best Models:**
- **Premium**: **DR Tulu-8B** (88.6% citation precision, 1000x cheaper than GPT-4)
- **Alternative**: GPT-4o, Claude 3.5 Sonnet
- **Balanced**: Gemini 2.5 Flash, GPT-4o Mini (citation bugs possible)

**Configuration:**
```bash
# Recommended: Use DR Tulu via LM Studio
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1235/v1

# Alternative: Use main model (may have citation bugs)
USE_DR_TULU_WRITER=false
WRITING_MODEL=gpt-4o
```

**Why DR Tulu-8B?**
- First open model trained for research with citations
- 88.6% citation precision (fixes phantom citations)
- Native `<cite id="SOURCE_N">` format prevents numbering errors
- $0.002/query vs $1.80 for GPT-4 (1000x cheaper)

---

## Configuration Strategies

### Strategy 1: Cloud-Only (Easiest)

**Use Case:** Quick start, no local setup

**Configuration:**
```bash
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

**All stages use:** Gemini 2.5 Flash

**Pros:**
- ✅ Easy setup (just API key)
- ✅ Fast performance
- ✅ Good quality

**Cons:**
- ❌ Citation bugs possible (no DR Tulu)
- ❌ Standard critique (no OLMo)
- ❌ Costs ~$0.10/report

**Quality Score:** 7/10

---

### Strategy 2: Privacy Mode (Local-Only)

**Use Case:** Sensitive research, no external APIs

**Configuration:**
```bash
RESEARCH_MODE=privacy
MODEL_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
```

**LM Studio:** Load one model (Qwen 2.5 7B, Llama 3.1 8B, etc.)

**All stages use:** Local model

**Pros:**
- ✅ Fully private
- ✅ No API costs
- ✅ No internet required

**Cons:**
- ❌ Slower (local inference)
- ❌ Lower quality than cloud
- ❌ Requires good hardware

**Quality Score:** 6/10

---

### Strategy 3: Hybrid Quality (RECOMMENDED FOR YOU)

**Use Case:** Best quality, optimize cost

**Configuration:**
```bash
# Cloud for basic stages (fast, cheap)
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your_key_here

# LM Studio for critical stages (quality)
USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1234/v1

USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1235/v1
```

**LM Studio Setup:**
- Instance 1 (port 1234): Olmo-3-32B-Think
- Instance 2 (port 1235): DR-Tulu-8B

**Stage Assignment:**
- Planning → Gemini 2.5 Flash
- Searching → Gemini 2.5 Flash
- Synthesis → Gemini 2.5 Flash
- **Critique → OLMo 3 32B Think (LM Studio)**
- **Writing → DR Tulu-8B (LM Studio)**

**Pros:**
- ✅ Best quality (enhanced critique + citation fix)
- ✅ Cost-effective (~$0.05/report, Gemini only for basic stages)
- ✅ Citation accuracy: 88.6%
- ✅ Enhanced reasoning in critique

**Cons:**
- ❌ Requires 2 LM Studio instances (~48GB RAM)
- ❌ More setup complexity

**Quality Score:** 9/10
**Cost:** $0.05/report
**Requirements:** Mac Mini M4 64GB (you have this!)

---

### Strategy 4: All-Local Multi-Model

**Use Case:** Maximum privacy + quality, powerful hardware

**Configuration:**
```bash
# Planning & basic stages
MODEL_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
PLANNER_MODEL=local-model

# Synthesis
SYNTHESIS_MODEL=local-model

# Critique (OLMo)
USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1236/v1

# Writing (DR Tulu)
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1237/v1
```

**LM Studio Setup:**
- Instance 1 (port 1234): Qwen 2.5 32B (planning/synthesis)
- Instance 2 (port 1236): Olmo-3-32B-Think (critique)
- Instance 3 (port 1237): DR-Tulu-8B (writing)

**Pros:**
- ✅ Fully local
- ✅ Best quality with specialized models
- ✅ No API costs

**Cons:**
- ❌ Requires 80GB+ RAM (3 models running)
- ❌ Complex setup (3 LM Studio instances)
- ❌ Slower than cloud

**Quality Score:** 9/10
**Requirements:** 128GB RAM workstation

---

## Your Recommended Setup

Based on your Mac Mini M4 64GB and requirements:

### Configuration (.env)

```bash
# ============================================================================
# RECOMMENDED SETUP: Hybrid Quality (Best for Mac Mini M4 64GB)
# ============================================================================

# Use Gemini for fast/cheap stages (Planning, Searching, Synthesis)
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Stage-specific overrides (optional fine-tuning)
# PLANNER_MODEL=gemini-2.5-flash
# SEARCH_MODEL=gemini-2.5-flash
# SYNTHESIS_MODEL=gemini-2.5-flash

# Use OLMo for enhanced critique (LM Studio port 1234)
USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1234/v1

# Use DR Tulu for citation-accurate writing (LM Studio port 1235)
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1235/v1

# Search APIs (at least one recommended)
SERPER_API_KEY=your_serper_key_here
TAVILY_API_KEY=your_tavily_key_here
```

### LM Studio Setup

1. **Start LM Studio Instance 1:**
   - Load: `Olmo-3-32B-Think`
   - Server → Port: `1234`
   - Start Server

2. **Start LM Studio Instance 2:**
   - Load: `DR-Tulu-8B`
   - Server → Port: `1235`
   - Start Server

### What You Get

| Stage | Model | Endpoint | Purpose |
|-------|-------|----------|---------|
| 1. Planning | Gemini 2.5 Flash | Cloud | Fast objective generation |
| 2. Searching | Gemini 2.5 Flash | Cloud | Fast query generation |
| 3. Synthesis | Gemini 2.5 Flash | Cloud | Efficient summarization |
| 4. Critique | **OLMo 3 32B Think** | LM Studio :1234 | **Enhanced reasoning** |
| 5. Writing | **DR Tulu-8B** | LM Studio :1235 | **88.6% citation precision** |

### Expected Results

**Before (Cloud-only):**
- Citation precision: 6.5/10 (broken)
- Quality evaluation: Standard
- Cost: $0.10/report

**After (Hybrid):**
- Citation precision: **88.6%** ✅
- Quality evaluation: **Enhanced with explicit reasoning** ✅
- Cost: **$0.05/report** (50% savings) ✅
- RAM usage: **~48GB** (fits in your 64GB) ✅

---

## Configuration Examples

### Example 1: Student Research (Budget)

```bash
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your_key
# All stages use Gemini 2.5 Flash
# Cost: ~$0.10/report
```

### Example 2: Professional Research (Quality)

```bash
MODEL_PROVIDER=openai
OPENAI_API_KEY=your_key
PLANNER_MODEL=gpt-4o  # Better reasoning
WRITING_MODEL=gpt-4o  # Better writing
# Cost: ~$0.50/report
```

### Example 3: Privacy Research (Local)

```bash
RESEARCH_MODE=privacy
MODEL_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
# LM Studio: Load Qwen 2.5 32B
# Cost: $0 (local)
```

### Example 4: Citation-Critical Research (Hybrid)

```bash
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your_key
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1234/v1
# LM Studio: Load DR-Tulu-8B
# Focus: Fix citation bugs
# Cost: ~$0.05/report
```

---

## Model Selection Guide

### When to Use Each Model

**Gemini 2.5 Flash:**
- ✅ Planning, Searching, Synthesis
- ✅ Fast, cheap, good quality
- ✅ Excellent for summarization
- ❌ Citation bugs possible

**GPT-4o / GPT-4o Mini:**
- ✅ Planning (strong reasoning)
- ✅ All-around good performance
- ❌ More expensive than Gemini
- ❌ Citation bugs possible

**OLMo 3 32B Think:**
- ✅ **Critique** (explicit reasoning)
- ✅ Planning (good logical thinking)
- ✅ Local deployment (privacy)
- ❌ Slower than cloud
- ❌ Requires 32GB RAM

**DR Tulu-8B:**
- ✅ **Writing** (88.6% citation precision)
- ✅ Research reports with citations
- ✅ 1000x cheaper than GPT-4
- ❌ Not for query generation
- ❌ Requires 16GB RAM

**Qwen 2.5 7B/32B:**
- ✅ All stages (local)
- ✅ Good quality for local model
- ✅ Fast on M-series Macs
- ❌ Lower quality than cloud

**Llama 3.1 8B/70B:**
- ✅ All stages (local)
- ✅ Open source, privacy
- ❌ Slower than Qwen on Mac

---

## Troubleshooting

### "Cannot connect to LM Studio"

**Check:**
```bash
curl http://localhost:1234/v1/models
```

**Should return:** JSON with model info

**Fix:**
1. Open LM Studio
2. Load model
3. Start server
4. Check port number matches .env

### "Citation bugs still happening"

**Verify DR Tulu is active:**
```bash
# Look for in logs:
🚀 Using DR Tulu-8B for report writing (88.6% citation precision)
DRTuluReportWriter initialized (endpoint: http://localhost:1235/v1, ...)
```

**Fix:**
1. Ensure `USE_DR_TULU_WRITER=true`
2. Verify LM Studio running on port 1235
3. Check DR-Tulu-8B is loaded

### "Out of memory with 2 LM Studio instances"

**Check RAM usage:**
```bash
# macOS
vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages free:\s+(\d+)/ and printf("%.2f GB free\n", $1*$size/1073741824);'
```

**RAM Requirements:**
- OLMo 3 32B: ~32GB
- DR Tulu-8B: ~16GB
- Total: ~48GB (fits in 64GB)

**Fix if tight:**
1. Close other apps
2. Use quantized models (Q4/Q5)
3. Use only DR Tulu (more critical than OLMo)

### "Quality scores too low"

**Enable self-correction:**
```bash
# Automatic - if critique score < 70, refines research
```

**Check in logs:**
```
Research quality insufficient (65/100) - refinement recommended
  Missing topics: X, Y, Z
  Recommended queries: 3
```

**Manual improvements:**
1. Add more search APIs (SERPER_API_KEY, TAVILY_API_KEY)
2. Increase search queries: `MAX_SEARCH_QUERIES=10`
3. Use better models for synthesis
4. Enable OLMo critic for better evaluation

---

## Summary

**Recommended Configuration for Mac Mini M4 64GB:**

1. **Use Gemini** for Planning, Searching, Synthesis (fast, cheap)
2. **Use OLMo** (LM Studio port 1234) for Critique (enhanced reasoning)
3. **Use DR Tulu** (LM Studio port 1235) for Writing (citation fix)

**Expected Improvement:**
- Citation accuracy: 6.5/10 → **88.6%**
- Quality evaluation: Standard → **Enhanced**
- Cost: $0.10 → **$0.05** per report

**Setup Time:** ~15 minutes (one-time)

---

See also:
- [LM Studio Setup Guide](LMSTUDIO_SETUP.md)
- [Sequential Workflow Guide](SEQUENTIAL_WORKFLOW.md)
- [DR Tulu & OLMo Setup](DR_TULU_OLMO_SETUP.md)
