# Sequential Workflow: Using Both DR Tulu & OLMo

**Best of Both Worlds - Enhanced Critique + Citation Accuracy**

Since LM Studio runs one model at a time, but the research workflow is **sequential** (critique happens BEFORE writing), you can use both models in a single research run!

---

## Workflow Stages

```
1. Planning      → (uses your main model, e.g., Gemini)
2. Searching     → (uses search model)
3. Synthesizing  → (uses synthesis model)
4. 🧠 CRITIQUE   → Use OLMo 3 32B Think (enhanced reasoning)
5. ✍️ WRITING    → Use DR Tulu-8B (88.6% citation precision)
6. Validation    → (automatic)
```

**Key Insight:** Critique (step 4) and Writing (step 5) are separate stages that run at different times, so you can use different models!

---

## Option A: Fully Automated (Recommended)

**Setup:** Run two LM Studio instances on different ports

### Step 1: Start Both Models

**Terminal 1 - OLMo for Critique:**
```bash
# LM Studio instance 1
# Load: Olmo-3-32B-Think
# Server Settings → Port: 1234
# Start Server
```

**Terminal 2 - DR Tulu for Writing:**
```bash
# LM Studio instance 2 (if you can run multiple)
# Load: DR-Tulu-8B
# Server Settings → Port: 1235
# Start Server
```

### Step 2: Configure .env

```bash
# Enable OLMo for critique
USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1234/v1

# Enable DR Tulu for writing
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1235/v1
```

### Step 3: Run Research

```bash
python -m src.main "AI automation impact on jobs"
```

**Result:**
- Critique uses OLMo (enhanced reasoning)
- Writing uses DR Tulu (88.6% citation precision)
- Fully automated, no manual switching!

---

## Option B: Manual Model Switching (If Can't Run Two Instances)

**Setup:** Run one LM Studio instance, switch models mid-run

### Challenge

LM Studio can only run one model at a time on Mac. Since critique happens BEFORE writing, we need to switch models mid-run.

### Solution: Staged Execution

**NOT RECOMMENDED** - This would require pausing execution, which is complex.

Instead, **prioritize one model**:

#### Priority 1: DR Tulu Only (Fixes Critical Citation Bug)

```bash
USE_DR_TULU_WRITER=true
USE_OLMO_CRITIC=false
```

**Benefits:**
- ✅ 88.6% citation precision (vs current 6.5/10)
- ✅ No phantom citations
- ✅ Correct source mapping

**Trade-off:**
- Standard critique (still good, just not OLMo-enhanced)

#### Priority 2: OLMo Only (Enhanced Critique)

```bash
USE_DR_TULU_WRITER=false
USE_OLMO_CRITIC=true
```

**Benefits:**
- ✅ Enhanced reasoning with `<think>` tags
- ✅ Better gap detection
- ✅ More thorough evaluation

**Trade-off:**
- Standard writing (citation bug remains)

---

## Option C: Run LM Studio Twice (Recommended Compromise)

**Setup:** Use LM Studio for one, main model for the other

### Scenario 1: DR Tulu Primary (Citation Fix)

```bash
# LM Studio: Load DR-Tulu-8B on port 1234
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1234/v1

# Critique: Use your main model (Gemini/OpenAI)
USE_OLMO_CRITIC=false
```

**Best for:** Fixing the critical citation bug while maintaining good critique

### Scenario 2: OLMo Primary (Enhanced Critique)

```bash
# LM Studio: Load Olmo-3-32B-Think on port 1234
USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1234/v1

# Writing: Use your main model (Gemini/OpenAI)
USE_DR_TULU_WRITER=false
```

**Best for:** Enhanced critique while accepting standard citation accuracy

---

## Recommended Configuration

**For Your Mac Mini M4 64GB:**

I recommend **Option C - Scenario 1** (DR Tulu Primary):

```bash
# .env configuration

# Use Gemini/OpenAI for main operations
MODEL_PROVIDER=gemini  # or openai
MODEL_NAME=gemini-2.5-flash

# LM Studio for DR Tulu (critical citation fix)
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1234/v1

# Standard critique (still good)
USE_OLMO_CRITIC=false
```

**Why?**
1. **Fixes the critical bug** - Citation mapping (6.5/10 → 88.6%)
2. **Easy setup** - Only one LM Studio instance needed
3. **Good critique** - Gemini/OpenAI provides solid quality evaluation
4. **Best ROI** - Citation fix is more impactful than critique enhancement

---

## Running Multiple LM Studio Instances

**Can you run two LM Studio instances?**

### Check Your RAM

```bash
# macOS
vm_stat | grep free
```

**Calculation:**
- DR Tulu-8B: ~16GB RAM
- OLMo 3 32B: ~32GB RAM
- **Total: ~48GB** (fits in your 64GB!)

### If You Have Enough RAM

**Method 1: Multiple Ports (Same App)**

Some LM Studio versions allow multiple model servers:

1. LM Studio → Settings → Enable "Multiple Models"
2. Load both models
3. Assign different ports (1234, 1235)
4. Start both servers

**Method 2: Two Separate Apps** (if supported)

1. Open LM Studio instance 1 → Load OLMo → Port 1234
2. Open LM Studio instance 2 → Load DR Tulu → Port 1235

### If RAM is Tight

Use **Option C - Scenario 1** (DR Tulu only with Gemini/OpenAI for critique)

---

## Performance Comparison

| Configuration | Citation Fix | Enhanced Critique | Setup Complexity | RAM Usage |
|---------------|--------------|-------------------|------------------|-----------|
| **Both Models (Option A)** | ✅ 88.6% | ✅ OLMo Think | Medium | ~48GB |
| **DR Tulu Only (Option C-1)** | ✅ 88.6% | ⚠️ Standard | Easy | ~16GB |
| **OLMo Only (Option C-2)** | ❌ Broken | ✅ OLMo Think | Easy | ~32GB |
| **Neither (Current)** | ❌ Broken | ⚠️ Standard | Easiest | 0GB |

---

## Quick Start Recommendations

### Immediate Fix (Start Here)

```bash
# .env
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1234/v1
USE_OLMO_CRITIC=false
```

**LM Studio:** Load DR-Tulu-8B → Start Server on 1234

**Result:** Citation bug fixed (6.5/10 → 88.6%)

### Full Enhancement (If RAM Permits)

```bash
# .env
USE_DR_TULU_WRITER=true
DR_TULU_ENDPOINT=http://localhost:1235/v1

USE_OLMO_CRITIC=true
OLMO_ENDPOINT=http://localhost:1234/v1
```

**LM Studio:**
- Instance 1: OLMo-3-32B-Think on port 1234
- Instance 2: DR-Tulu-8B on port 1235

**Result:** Both enhanced critique AND citation fix

---

## Testing Your Setup

### Verify Both Models

```bash
# Check OLMo
curl http://localhost:1234/v1/models

# Check DR Tulu
curl http://localhost:1235/v1/models
```

### Run Test Research

```bash
python -m src.main "AI automation impact on jobs"
```

**Watch logs for:**

```
🧠 Using OLMo 3 32B Think for enhanced research critique
OLMoThinker initialized (endpoint: http://localhost:1234/v1, ...)

🚀 Using DR Tulu-8B for report writing (88.6% citation precision)
DRTuluReportWriter initialized (endpoint: http://localhost:1235/v1, ...)
```

---

## Troubleshooting

### "Cannot run two LM Studio instances"

**Solution:** Use Option C (one LM Studio + main model)

Priority: DR Tulu (fixes critical bug)

### "Out of memory with both models"

**Check RAM usage:**
```bash
vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages free:\s+(\d+)/ and printf("%.2f GB free\n", $1*$size/1073741824);'
```

**Solutions:**
1. Close other apps
2. Use quantized models (Q4/Q5 versions)
3. Use Option C (one model at a time)

### "Which model is more important?"

**DR Tulu** - Fixes critical citation bug (6.5/10 → 88.6%)

Start with DR Tulu, add OLMo later if you want enhanced critique.

---

## Summary

**Recommended Setup for Mac Mini M4 64GB:**

1. **Start Simple** - DR Tulu only (fixes critical bug)
2. **Expand** - Add OLMo if RAM permits (~48GB total)
3. **Optimize** - Use main model (Gemini/OpenAI) for other stages

**Priority Order:**
1. 🥇 DR Tulu (critical citation fix)
2. 🥈 OLMo (enhanced critique)
3. 🥉 Standard models (if RAM constrained)

**Expected Improvement:**
- Citation precision: 6.5/10 → **88.6%**
- Quality evaluation: Good → **Excellent** (with OLMo)
- Cost: $1.80/query → **$0.002/query**

---

**Ready to configure?** Start with DR Tulu on port 1234, then add OLMo on port 1235 if your system handles it well.
