# LM Studio Setup for DR Tulu & OLMo

**Easy Setup for macOS Users (Mac Mini M4)**

LM Studio is the recommended way to run DR Tulu and OLMo on macOS. It's easier than VLLM and has a user-friendly interface.

---

## Why LM Studio?

✅ **Easier setup** - No command-line configuration
✅ **Works on macOS** - Native Metal support for M-series chips
✅ **User-friendly** - GUI for model management
✅ **No Python dependencies** - Standalone application
✅ **Same API** - OpenAI-compatible endpoint

❌ **One model at a time** - Can't run DR Tulu + OLMo simultaneously
✅ **Solution** - Prioritize DR Tulu (fixes critical citation bugs)

---

## Installation

### Step 1: Download LM Studio

1. Visit https://lmstudio.ai
2. Download for macOS
3. Install and open LM Studio

### Step 2: Download DR Tulu Model

1. Click the **Search** icon (🔍) in LM Studio
2. Search for: `DR-Tulu-8B`
3. Find: **rl-research/DR-Tulu-8B**
4. Click **Download**

**Size**: ~16GB
**Time**: 10-30 minutes depending on internet speed

---

## Configuration

### Step 3: Load DR Tulu in LM Studio

1. Click the **↔️** icon (Local Server) in the sidebar
2. Click **Select a model to load**
3. Choose **rl-research/DR-Tulu-8B**
4. Click **Load Model**

Wait ~30 seconds for model to load into memory.

### Step 4: Start the Server

1. In the **Local Server** tab
2. Click **Start Server**
3. You should see: `Server running on http://localhost:1234`

**Important**: Note the "Served Model Name" shown in the interface.
Usually it's something like `local-model` or `rl-research/DR-Tulu-8B`.

### Step 5: Configure Deep Research Agent

Add to your `.env` file:

```bash
# Enable DR Tulu for citation accuracy
USE_DR_TULU_WRITER=true

# LM Studio endpoint (default port 1234)
DR_TULU_ENDPOINT=http://localhost:1234/v1

# Model name (optional, usually auto-detects)
# Only needed if you get connection errors
# DR_TULU_MODEL_NAME=local-model
```

---

## Testing

### Verify Server is Running

```bash
# Test the endpoint
curl http://localhost:1234/v1/models

# Should return JSON with model info
{
  "object": "list",
  "data": [
    {
      "id": "local-model",
      "object": "model",
      ...
    }
  ]
}
```

### Run a Test Query

```bash
python -m src.main "AI automation impact on jobs"
```

**Look for in logs:**
```
🚀 Using DR Tulu-8B for report writing (88.6% citation precision)
DRTuluReportWriter initialized (endpoint: http://localhost:1234/v1, model: local-model)
```

---

## Troubleshooting

### Error: "Cannot connect to localhost:1234"

**Cause**: Server not running

**Solution**:
1. Open LM Studio
2. Go to Local Server tab (↔️)
3. Click **Start Server**
4. Wait for "Server running" message

### Error: "Model not found"

**Cause**: Model name mismatch

**Solution**:

1. In LM Studio, check **Local Server** tab
2. Find "Served Model Name" (e.g., `local-model`)
3. Add to `.env`:
   ```bash
   DR_TULU_MODEL_NAME=local-model
   ```

### Error: "Out of memory"

**Cause**: Not enough RAM

**Solution**:

Your Mac Mini M4 with 64GB RAM should be fine. If issues:

1. In LM Studio: **Settings** → **Performance**
2. Reduce **GPU Offload** layers
3. Or use a quantized version:
   - Search for `DR-Tulu-8B-GGUF`
   - Download Q4 or Q5 version (smaller)

### Slow Generation

**Cause**: CPU-only inference

**Solution**:

1. LM Studio → **Settings** → **Performance**
2. Enable **GPU Acceleration** (Metal on macOS)
3. Increase **GPU Offload** to maximum

---

## Advanced Configuration

### Custom Port

If port 1234 is in use:

1. LM Studio → **Settings** → **Server**
2. Change port to (e.g.) `8080`
3. Update `.env`:
   ```bash
   DR_TULU_ENDPOINT=http://localhost:8080/v1
   ```

### Generation Parameters

In LM Studio → **Local Server** → **Server Options**:

- **Temperature**: 0.7 (recommended for research)
- **Max Tokens**: 4096 (for longer sections)
- **Context Length**: 8192+ (for more sources)

### Model Switching (DR Tulu ↔ OLMo)

Since LM Studio runs one model at a time:

**For DR Tulu (citation accuracy)**:
1. Load DR-Tulu-8B
2. Start server
3. `.env`: `USE_DR_TULU_WRITER=true`, `USE_OLMO_CRITIC=false`

**For OLMo (enhanced critique)**:
1. Stop server
2. Load Olmo-3-32B-Think
3. Start server
4. `.env`: `USE_DR_TULU_WRITER=false`, `USE_OLMO_CRITIC=true`

**Recommendation**: Start with DR Tulu - it fixes the critical citation bug.

---

## Performance Expectations

### Mac Mini M4 64GB

- **Model loading**: ~30 seconds
- **Section generation**: ~10-30 seconds per section
- **Memory usage**: ~16GB for DR Tulu
- **Token speed**: ~20-50 tokens/second

### Compared to VLLM

| Metric | LM Studio | VLLM |
|--------|-----------|------|
| Setup difficulty | ⭐⭐ Easy | ⭐⭐⭐⭐⭐ Complex |
| macOS support | ✅ Native | ❌ Issues |
| GUI | ✅ Yes | ❌ Command-line only |
| Speed | Good | Excellent |
| Multi-model | ❌ One at a time | ✅ Multiple |

---

## Finding Model Names

If you need to manually specify the model name:

### Method 1: Check LM Studio Interface

1. LM Studio → **Local Server** tab
2. Look for "Served Model Name"
3. Copy the exact name shown

### Method 2: Use API

```bash
curl http://localhost:1234/v1/models | jq '.data[0].id'
```

Common values:
- `local-model`
- `rl-research/DR-Tulu-8B`
- `DR-Tulu-8B`

### Method 3: Check Logs

When you run research, look for:
```
DRTuluReportWriter initialized (endpoint: http://localhost:1234/v1, model: local-model)
```

If it says `model: rl-research/DR-Tulu-8B` but fails, try:
```bash
DR_TULU_MODEL_NAME=local-model
```

---

## Comparison: LM Studio vs VLLM

### Use LM Studio If:

- ✅ You're on macOS (especially M-series Mac)
- ✅ You want easy setup
- ✅ You prefer GUI over command-line
- ✅ You're okay running one model at a time
- ✅ VLLM installation fails (torch version issues)

### Use VLLM If:

- You're on Linux with NVIDIA GPU
- You need to run multiple models simultaneously
- You want maximum performance
- You're comfortable with command-line tools

---

## Next Steps

1. ✅ Install LM Studio
2. ✅ Download DR-Tulu-8B
3. ✅ Load model and start server
4. ✅ Configure `.env` with LM Studio endpoint
5. ✅ Test with sample research query
6. ✅ Verify citation accuracy improved

**Expected Results:**
- ✅ 88.6% citation precision
- ✅ No phantom citations
- ✅ Proper source-citation mapping
- ✅ Quality rating: 6.5/10 → 9/10

---

## Support

### Check Server Status

```bash
# Is server running?
curl http://localhost:1234/v1/models

# Check model info
curl http://localhost:1234/v1/models | jq
```

### Enable Debug Logging

In `.env`:
```bash
LOG_LEVEL=DEBUG
```

Check logs for:
```
DRTuluReportWriter initialized (endpoint: ..., model: ...)
Writing section with DR Tulu: ...
DR Tulu section complete: ...
```

### Common Issues

1. **Server not starting**: Restart LM Studio
2. **Model not loading**: Check available RAM (need 16GB+)
3. **Slow generation**: Enable GPU acceleration in settings
4. **Connection refused**: Verify port 1234 is not blocked

---

## Summary

**LM Studio Setup (3 Steps)**:

1. Download LM Studio → Load DR-Tulu-8B
2. Start server on port 1234
3. Add to `.env`:
   ```bash
   USE_DR_TULU_WRITER=true
   DR_TULU_ENDPOINT=http://localhost:1234/v1
   ```

**Benefits**:
- ✅ Fixes citation bugs (88.6% precision)
- ✅ Easy macOS setup
- ✅ No VLLM installation issues
- ✅ User-friendly interface

**Limitation**: One model at a time (prioritize DR Tulu for critical citation fix)

---

**Ready to test!** Run research and watch for citation accuracy improvements.
