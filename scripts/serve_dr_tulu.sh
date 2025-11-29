#!/bin/bash
# Serve DR Tulu-8B locally via VLLM
# Requires: pip install vllm

set -e

echo "🚀 Starting DR Tulu-8B server..."

# Configuration
MODEL_NAME="rl-research/DR-Tulu-8B"
PORT=30001
MAX_MODEL_LEN=40960
GPU_MEMORY_UTILIZATION=0.85

# Check if VLLM is installed
if ! python -c "import vllm" 2>/dev/null; then
    echo "❌ VLLM not installed. Installing..."
    pip install vllm
fi

# Check if model is already downloaded
echo "📦 Checking model availability..."
python -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL_NAME')" || {
    echo "❌ Failed to download model. Check HuggingFace access."
    exit 1
}

# Start VLLM server
echo "✅ Starting VLLM server on port $PORT..."
echo "   Model: $MODEL_NAME"
echo "   Max context: $MAX_MODEL_LEN tokens"
echo "   GPU memory: ${GPU_MEMORY_UTILIZATION}%"
echo ""
echo "OpenAI-compatible endpoint: http://localhost:$PORT/v1"
echo ""

vllm serve "$MODEL_NAME" \
    --port $PORT \
    --max-model-len $MAX_MODEL_LEN \
    --gpu-memory-utilization $GPU_MEMORY_UTILIZATION \
    --trust-remote-code
