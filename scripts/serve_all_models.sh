#!/bin/bash
# Start both DR Tulu and OLMo 3 32B Think servers
# Run in separate tmux/screen sessions or background processes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting all local models..."
echo ""

# Check if tmux is available
if command -v tmux &> /dev/null; then
    echo "Using tmux for session management..."

    # Start DR Tulu in tmux session
    tmux new-session -d -s dr-tulu "bash $SCRIPT_DIR/serve_dr_tulu.sh"
    echo "✅ DR Tulu server started in tmux session 'dr-tulu'"

    # Start OLMo Think in tmux session
    tmux new-session -d -s olmo-think "bash $SCRIPT_DIR/serve_olmo_think.sh"
    echo "✅ OLMo Think server started in tmux session 'olmo-think'"

    echo ""
    echo "📋 Management commands:"
    echo "   View DR Tulu logs:    tmux attach -t dr-tulu"
    echo "   View OLMo logs:       tmux attach -t olmo-think"
    echo "   Stop DR Tulu:         tmux kill-session -t dr-tulu"
    echo "   Stop OLMo:            tmux kill-session -t olmo-think"
    echo "   Stop all:             tmux kill-server"

else
    echo "⚠️  tmux not found. Starting in background processes..."

    # Start in background with nohup
    nohup bash "$SCRIPT_DIR/serve_dr_tulu.sh" > logs/dr-tulu.log 2>&1 &
    DR_TULU_PID=$!
    echo "✅ DR Tulu server started (PID: $DR_TULU_PID)"

    nohup bash "$SCRIPT_DIR/serve_olmo_think.sh" > logs/olmo-think.log 2>&1 &
    OLMO_PID=$!
    echo "✅ OLMo Think server started (PID: $OLMO_PID)"

    echo ""
    echo "📋 Management commands:"
    echo "   View DR Tulu logs:    tail -f logs/dr-tulu.log"
    echo "   View OLMo logs:       tail -f logs/olmo-think.log"
    echo "   Stop DR Tulu:         kill $DR_TULU_PID"
    echo "   Stop OLMo:            kill $OLMO_PID"
fi

echo ""
echo "⏳ Waiting for servers to start (30s)..."
sleep 5

# Health check
echo ""
echo "🏥 Health check..."

check_endpoint() {
    local name=$1
    local port=$2

    if curl -s "http://localhost:$port/v1/models" > /dev/null 2>&1; then
        echo "   ✅ $name (port $port) - READY"
        return 0
    else
        echo "   ⏳ $name (port $port) - Starting..."
        return 1
    fi
}

# Wait up to 60 seconds for both servers
TIMEOUT=60
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    DR_READY=false
    OLMO_READY=false

    check_endpoint "DR Tulu" 30001 && DR_READY=true
    check_endpoint "OLMo Think" 30002 && OLMO_READY=true

    if [ "$DR_READY" = true ] && [ "$OLMO_READY" = true ]; then
        echo ""
        echo "🎉 All servers ready!"
        echo ""
        echo "Endpoints:"
        echo "   DR Tulu:     http://localhost:30001/v1"
        echo "   OLMo Think:  http://localhost:30002/v1"
        exit 0
    fi

    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

echo ""
echo "⚠️  Timeout waiting for servers. Check logs for errors."
exit 1
