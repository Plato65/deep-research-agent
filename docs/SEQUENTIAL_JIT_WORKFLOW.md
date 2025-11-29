# Sequential Model Loading with LM Studio JIT

**One Server, Multiple Models, Automatic Switching**

---

## Overview

LM Studio's JIT (Just-In-Time) loading enables **sequential model loading** without manual intervention:

- ✅ Single LM Studio server (port 1234)
- ✅ Multiple models configured
- ✅ Automatic load/unload on request
- ✅ One model in memory at a time
- ✅ No manual switching needed!

---

## How It Works

### LM Studio JIT Features

**Auto-Loading:**
```bash
# Request model A
curl -X POST http://localhost:1234/v1/chat/completions \
  -d '{"model": "olmo-3-32b-instruct", "messages": [...]}'
# → LM Studio loads olmo-3-32b-instruct

# Request model B
curl -X POST http://localhost:1234/v1/chat/completions \
  -d '{"model": "dr-tulu-8b", "messages": [...]}'
# → LM Studio auto-loads dr-tulu-8b
# → Auto-evicts olmo-3-32b-instruct
```

**Auto-Evict (Default: ON):**
- Unloads previous model when loading new one
- Keeps only ONE model in memory
- Perfect for Mac Mini M4 64GB!

**Idle TTL (Default: 60 minutes):**
- Model stays loaded for 60 minutes without requests
- Automatically unloads after idle period
- Configurable in LM Studio settings

---

## Your Workflow (Sequential Loading)

### Stage Flow

```
┌────────────────────────────────────────────────────────┐
│ STAGE 1: PLANNING                                      │
│ Model: olmo-3-32b-instruct (32GB)                     │
│ LM Studio: Auto-loads OLMo 3 32B                      │
│ Action: Generate research objectives and queries      │
└────────────────────────────────────────────────────────┘
              ↓ (Model auto-evicted)
┌────────────────────────────────────────────────────────┐
│ STAGE 2: SEARCHING                                     │
│ Model: qwen3-8b-instruct (8GB)                        │
│ LM Studio: Auto-loads Qwen3 8B, evicts OLMo          │
│ Action: Generate search queries                       │
└────────────────────────────────────────────────────────┘
              ↓ (Model stays loaded - same model)
┌────────────────────────────────────────────────────────┐
│ STAGE 3: SYNTHESIS                                     │
│ Model: qwen3-8b-instruct (reuses)                     │
│ LM Studio: No reload needed (same model)             │
│ Action: Summarize search results                      │
└────────────────────────────────────────────────────────┘
              ↓ (Model auto-evicted)
┌────────────────────────────────────────────────────────┐
│ STAGE 4: CRITIQUE                                      │
│ Model: olmo-3-32b-instruct (32GB)                     │
│ LM Studio: Auto-loads OLMo 3 32B, evicts Qwen3       │
│ Action: Evaluate research quality                     │
└────────────────────────────────────────────────────────┘
              ↓ (Model auto-evicted)
┌────────────────────────────────────────────────────────┐
│ STAGE 5: WRITING                                       │
│ Model: dr-tulu-8b (16GB)                              │
│ LM Studio: Auto-loads DR Tulu, evicts OLMo           │
│ Action: Write report with citations                   │
└────────────────────────────────────────────────────────┘
```

### Memory Usage

**Peak RAM (one model at a time):**
- OLMo 3 32B: ~32GB
- DR Tulu-8B: ~16GB
- Qwen3 8B: ~8GB

**Your Mac Mini M4 64GB:** ✅ Perfect fit!

---

## Configuration

### Option A: All Local (Sequential)

**.env:**
```bash
# Use LM Studio for all stages
MODEL_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Stage-specific models (JIT auto-loads)
PLANNER_MODEL=olmo-3-32b-instruct      # Strong reasoning
SEARCH_MODEL=qwen3-8b-instruct         # Fast queries
SYNTHESIS_MODEL=qwen3-8b-instruct      # Fast summarization

# Specialized models (same endpoint!)
USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1234/v1
OLMO_MODEL_NAME=olmo-3-32b-instruct

USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1234/v1
DR_TULU_MODEL_NAME=dr-tulu-8b
```

**Result:**
- ✅ Fully local (no API costs)
- ✅ One model at a time (~32GB max)
- ✅ Automatic switching (JIT)
- ✅ Quality: 9/10
- ✅ Cost: $0

---

### Option B: Hybrid (Cloud + Local)

**.env:**
```bash
# Use Gemini for fast/cheap stages
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your_key_here

# Planning, Search, Synthesis → Gemini
# (Uses MODEL_PROVIDER default)

# Critical stages → LM Studio
USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1234/v1
OLMO_MODEL_NAME=olmo-3-32b-instruct

USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1234/v1
DR_TULU_MODEL_NAME=dr-tulu-8b
```

**Result:**
- ✅ Fast basic stages (Gemini)
- ✅ Quality critical stages (LM Studio)
- ✅ Lower RAM usage (only 2 models loaded sequentially)
- ✅ Quality: 9/10
- ✅ Cost: ~$0.05/report

---

### Option C: Mix and Match

**.env:**
```bash
# Mix cloud and local per stage
MODEL_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Planning: Local OLMo (best reasoning)
PLANNER_MODEL=olmo-3-32b-instruct

# Search: Cloud Gemini (fastest)
SEARCH_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_key_here

# Synthesis: Local Qwen3 (privacy)
SYNTHESIS_MODEL=qwen3-8b-instruct

# Critique: Local OLMo (quality)
USE_OLMO_CRITIC=true
OLMO_MODEL_NAME=olmo-3-32b-instruct

# Writing: Local DR Tulu (citations)
USE_DR_TULU_WRITER=true
DR_TULU_MODEL_NAME=dr-tulu-8b
```

**Result:**
- ✅ Optimize each stage independently
- ✅ Balance speed, cost, quality, privacy
- ✅ Maximum flexibility

---

## Setup Steps

### 1. Prepare LM Studio

**Download Models:**
- OLMo 3 32B Instruct (for planning & critique)
- DR Tulu-8B (for writing)
- Qwen3 8B Instruct (for search & synthesis)

**Configure Server:**
1. Open LM Studio
2. Go to **Settings** → **Server**
3. Enable **Auto-Evict**: ON (one model at a time)
4. Set **Idle TTL**: 60 minutes (or longer)
5. Port: 1234 (default)

**Start Server:**
1. Go to **Server** tab
2. Click **Start Server**
3. Verify: `curl http://localhost:1234/v1/models`

### 2. Find Model Names

**Method 1: LM Studio UI**
- Server tab → "Served Model Name" field
- Note the exact name for each model

**Method 2: API Query**
```bash
curl http://localhost:1234/v1/models | jq '.data[].id'
```

**Common Patterns:**
- `local-model` (generic)
- `olmo-3-32b-instruct`
- `dr-tulu-8b`
- `qwen3-8b-instruct`
- `mlx-community/OLMo-3-32B-Instruct-4bit` (MLX format)

### 3. Configure .env

Copy `.env.template` → `.env` and set:

```bash
MODEL_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Use EXACT model names from step 2
PLANNER_MODEL=olmo-3-32b-instruct
SEARCH_MODEL=qwen3-8b-instruct
SYNTHESIS_MODEL=qwen3-8b-instruct

USE_OLMO_CRITIC=true
OLMO_MODEL_NAME=olmo-3-32b-instruct

USE_DR_TULU_WRITER=true
DR_TULU_MODEL_NAME=dr-tulu-8b
```

### 4. Test

```bash
python -m src.main "AI automation impact on jobs"
```

**Watch logs for:**
```
Planning stage: Loading olmo-3-32b-instruct...
Searching stage: Loading qwen3-8b-instruct...
Synthesis stage: Using qwen3-8b-instruct (already loaded)...
🧠 Using OLMo 3 32B Think for enhanced research critique
   Loading olmo-3-32b-instruct...
🚀 Using DR Tulu-8B for report writing (88.6% citation precision)
   Loading dr-tulu-8b...
```

---

## Performance Expectations

### Model Loading Times (First Request)

| Model | Size | Load Time | Inference Speed |
|-------|------|-----------|-----------------|
| Qwen3 8B | 8GB | ~10-15s | Fast (50+ tok/s) |
| DR Tulu-8B | 16GB | ~20-30s | Medium (30-40 tok/s) |
| OLMo 3 32B | 32GB | ~40-60s | Slower (15-25 tok/s) |

**MLX Models (Mac M-series):**
- 2-3x faster inference
- Faster loading
- Better memory efficiency

### Total Research Time

**Typical Research (5 search queries, 20 sources):**

| Stage | Time | Model |
|-------|------|-------|
| Planning | 30s + 15s load | OLMo 3 32B |
| Searching | 60s + 10s load | Qwen3 8B |
| Synthesis | 45s (reuses) | Qwen3 8B |
| Critique | 40s + 60s load | OLMo 3 32B |
| Writing | 120s + 30s load | DR Tulu-8B |
| **Total** | **~6-7 minutes** | Sequential |

**With Cloud (Hybrid):**
- Planning: 5s (Gemini)
- Searching: 30s (Gemini)
- Synthesis: 10s (Gemini)
- Critique: 40s + 60s load (LM Studio)
- Writing: 120s + 30s load (LM Studio)
- **Total: ~5 minutes**

---

## Troubleshooting

### "Model not found" Error

**Cause:** Model name mismatch

**Check:**
```bash
curl http://localhost:1234/v1/models | jq '.data[].id'
```

**Fix:** Use exact name in .env
```bash
PLANNER_MODEL=olmo-3-32b-instruct  # Must match exactly
```

### "Out of memory" Error

**Cause:** Auto-Evict disabled, multiple models loaded

**Fix:**
1. LM Studio → Settings → Server
2. Enable **Auto-Evict**: ON
3. Restart LM Studio server

### Slow First Request

**Expected Behavior:**
- First request loads model (30-60s)
- Subsequent requests fast

**Optimization:**
- Use smaller models for fast stages (Qwen3 8B)
- Use larger models only for critical stages (OLMo, DR Tulu)
- Preload model: `curl -X POST http://localhost:1234/v1/chat/completions -d '{"model": "your-model", "messages": [{"role": "user", "content": "hi"}]}'`

### Model Keeps Unloading

**Cause:** Idle TTL too short

**Fix:**
1. LM Studio → Settings → Server
2. Increase **Idle TTL**: 120 minutes (or 0 for infinite)

### Want Multiple Models Loaded

**Option 1:** Disable Auto-Evict
- Settings → Server → Auto-Evict: OFF
- Requires enough RAM for all models

**Option 2:** Run multiple LM Studio instances
- Instance 1: Port 1234 (OLMo)
- Instance 2: Port 1235 (DR Tulu)
- Different endpoints in .env

---

## MLX Models (Mac M-series Optimization)

### What is MLX?

- Apple's ML framework for M-series chips
- 2-3x faster than standard models on Mac
- Better memory efficiency
- Native Metal acceleration

### Finding MLX Models

**HuggingFace:**
- Search: "MLX OLMo", "MLX DR Tulu", "MLX Qwen3"
- Format: `mlx-community/model-name`

**Example:**
```
mlx-community/OLMo-3-32B-Instruct-4bit
mlx-community/Qwen3-8B-Instruct-MLX
```

### Using MLX Models

**.env:**
```bash
PLANNER_MODEL=mlx-community/OLMo-3-32B-Instruct-4bit
SEARCH_MODEL=mlx-community/Qwen3-8B-Instruct-MLX
```

**Benefits:**
- ✅ 2-3x faster inference
- ✅ Lower memory usage (4-bit quantization)
- ✅ Better suited for Mac M4

---

## Summary

**Sequential JIT Loading with LM Studio:**

✅ **One Server:** Single endpoint (port 1234)
✅ **Multiple Models:** Different model per stage
✅ **Automatic Switching:** JIT loads requested model
✅ **Auto-Evict:** One model at a time
✅ **No Manual Intervention:** Fully automated
✅ **Flexible:** Mix cloud + local models
✅ **Efficient:** ~32GB peak RAM (fits Mac Mini M4 64GB)

**Recommended Configuration:**
```bash
MODEL_PROVIDER=lmstudio
PLANNER_MODEL=olmo-3-32b-instruct
SEARCH_MODEL=qwen3-8b-instruct
SYNTHESIS_MODEL=qwen3-8b-instruct
USE_OLMO_CRITIC=true (olmo-3-32b-instruct)
USE_DR_TULU_WRITER=true (dr-tulu-8b)
```

**Expected Results:**
- Quality: 9/10
- Citation Accuracy: 88.6%
- Cost: $0 (fully local)
- Time: ~6-7 minutes per research
- RAM: One model at a time (~32GB peak)

---

See also:
- [Configuration Guide](CONFIGURATION_GUIDE.md)
- [LM Studio Setup](LMSTUDIO_SETUP.md)
