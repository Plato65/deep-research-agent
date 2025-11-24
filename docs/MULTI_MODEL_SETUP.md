# Multi-Model Setup Guide

Configure different models for each agent to optimize performance, cost, and quality.

## Quick Start

```bash
# .env
MODEL_PROVIDER=ollama

# Different models per agent
PLANNER_MODEL=qwen3-next-80b     # Reasoning-heavy
SEARCH_MODEL=hermes-4-70b        # Tool-use expert
SYNTHESIS_MODEL=qwen3-next-80b   # Multi-document analysis
WRITING_MODEL=mistral3-24b       # Fast, quality prose
```

## Memory Management (CRITICAL)

### The Problem
Loading multiple large models simultaneously exceeds RAM:

```
qwen3-next-80b: ~45GB
hermes-4-70b:   ~40GB
mistral3-24b:   ~26GB
Total:          111GB  ← Exceeds 64GB RAM!
```

### The Solution: Lazy Loading
Models load only when needed, unload between stages:

```python
# Workflow execution:
1. Planner loads qwen3-next-80b  → runs → unloads
2. Searcher loads hermes-4-70b   → runs → unloads
3. Synthesizer loads qwen3-next-80b → runs → unloads
4. Writer loads mistral3-24b     → runs → done

Peak memory: <50GB  ✓
```

### How It Works
```python
class ResearchPlanner:
    def __init__(self):
        self.model_name = "qwen3-next-80b"
        self.llm = None  # Not loaded yet!

    async def plan(self, state):
        self._ensure_llm_loaded()  # Load now
        # ... do planning ...

    def unload_model(self):
        ollama.stop(self.model_name)  # Free memory
```

## Model Selection Guide

### Planner (Reasoning)
**Best**: Large reasoning models
- qwen3-next-80b (recommended)
- llama3-70b
- mixtral-8x7b

**Why**: Planning requires strong reasoning to create objectives, queries, outline

### Searcher (Tool Use)
**Best**: Tool-use specialists
- hermes-4-70b (recommended)
- llama3.3-70b
- qwen2.5-coder

**Why**: Search agent uses tools autonomously (web_search, extract_content)

### Synthesizer (Analysis)
**Best**: Multi-document comprehension
- qwen3-next-80b (recommended)
- llama3-70b
- claude-3-sonnet (API)

**Why**: Synthesis requires understanding multiple sources, finding patterns

### Writer (Prose Quality)
**Best**: Fast, high-quality writing
- mistral3-24b (recommended)
- qwen2.5-32b
- gpt-4o-mini (API)

**Why**: Writing needs speed + quality, doesn't require massive reasoning

## Example Configurations

### All-Local (64GB RAM)
```bash
MODEL_PROVIDER=ollama

PLANNER_MODEL=qwen3-next-80b      # 45GB
SEARCH_MODEL=hermes-4-70b         # 40GB
SYNTHESIS_MODEL=qwen3-next-80b    # Reuses loaded model
WRITING_MODEL=mistral3-24b        # 26GB
```

**Works because**: Models unload between stages

### Hybrid (Cost Optimization)
```bash
MODEL_PROVIDER=ollama

# Local for search/planning (slow operations)
PLANNER_MODEL=qwen2.5-32b
SEARCH_MODEL=qwen2.5-32b

# API for synthesis/writing (quality-critical)
SYNTHESIS_MODEL=gpt-4o-mini  # OpenAI API
WRITING_MODEL=gpt-4o         # OpenAI API
```

### All-API (Simplicity)
```bash
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o-mini

# All agents use same model (no overrides needed)
```

### Mac Mini M4 64GB (Recommended)
```bash
MODEL_PROVIDER=ollama

# Test with smaller models first
PLANNER_MODEL=qwen2.5-32b
SEARCH_MODEL=qwen2.5-32b
SYNTHESIS_MODEL=qwen2.5-32b
WRITING_MODEL=qwen2.5-32b

# Then upgrade writer if quality needs improvement
WRITING_MODEL=mistral3-24b

# Then upgrade planner/synthesizer
PLANNER_MODEL=qwen3-next-80b
SYNTHESIS_MODEL=qwen3-next-80b

# Finally upgrade searcher
SEARCH_MODEL=hermes-4-70b
```

## Monitoring

### Startup Logs
```
INFO: ResearchPlanner initialized (lazy load: qwen3-next-80b)
INFO: ResearchSearcher initialized (lazy load: hermes-4-70b)
INFO: ResearchSynthesizer initialized (lazy load: qwen3-next-80b)
INFO: ReportWriter initialized (lazy load: mistral3-24b)
```

### Execution Logs
```
INFO: Loading Planner LLM: qwen3-next-80b
INFO: Unloaded Planner model: qwen3-next-80b
INFO: Loading Searcher LLM: hermes-4-70b
INFO: Unloaded Searcher model: hermes-4-70b
...
```

### Memory Monitoring
```bash
# During execution, check Ollama models
ollama ps

# Should show only ONE model loaded at a time
```

## Troubleshooting

### "Out of memory" error
**Cause**: Models not unloading properly
**Fix**: Check Ollama is running (`ollama serve`)

### "Model not found" error
**Cause**: Model name mismatch
**Fix**: Verify with `ollama list`, use exact name

### Slow execution
**Cause**: Large models loading/unloading frequently
**Fix**: Use smaller models for non-critical agents

### High costs (API)
**Cause**: Large model for all agents
**Fix**: Use cheap models for planner/searcher, expensive for writer

## Performance Tips

1. **Reuse models**: Same model for planner + synthesizer (loaded once)
2. **Fast search**: Use smaller model for search agent (tool-use focused)
3. **Quality writing**: Use best model only for final writing
4. **Monitor costs**: Track token usage per agent in logs

## Fallback Behavior

If agent-specific model not set, falls back to:
- Planner → `MODEL_NAME`
- Search → `MODEL_NAME`
- Synthesizer → `SUMMARIZATION_MODEL`
- Writer → `MODEL_NAME`

This ensures backward compatibility with single-model setup.
