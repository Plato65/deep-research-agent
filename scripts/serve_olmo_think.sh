#!/bin/bash
# Serve OLMo 3 32B Think locally via VLLM
# Requires: pip install vllm transformers>=4.57.0

set -e

echo "🚀 Starting OLMo 3 32B Think server..."

# Configuration
MODEL_NAME="allenai/Olmo-3-32B-Think"
PORT=30002
MAX_MODEL_LEN=32768
GPU_MEMORY_UTILIZATION=0.85

# Check if VLLM is installed
if ! python -c "import vllm" 2>/dev/null; then
    echo "❌ VLLM not installed. Installing..."
    pip install vllm
fi

# Check transformers version
python -c "import transformers; assert tuple(map(int, transformers.__version__.split('.')[:2])) >= (4, 57), 'Transformers >= 4.57.0 required'" || {
    echo "❌ Transformers >= 4.57.0 required. Upgrading..."
    pip install "transformers>=4.57.0"
}

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
