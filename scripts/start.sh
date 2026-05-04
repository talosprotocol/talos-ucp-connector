#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Start Talos UCP Connector
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="talos-ucp-connector"
PID_FILE="/tmp/${SERVICE_NAME}.pid"
LOG_FILE="/tmp/${SERVICE_NAME}.log"

# Default to SSE for background service mode
export MCP_TRANSPORT="${MCP_TRANSPORT:-sse}"
export PORT="${PORT:-8084}"

cd "$REPO_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "$SERVICE_NAME is already running"
    exit 0
fi

echo "Starting $SERVICE_NAME on port $PORT (transport: $MCP_TRANSPORT)..."

# Use uvicorn directly if FastMCP.run(transport="sse") is just a wrapper,
# or use the talos-ucp CLI if it's properly installed.
# The main.py in ucp-connector has a main() function.
PYTHONPATH=src nohup python3 src/talos_ucp_connector/adapters/inbound/mcp_server.py > "$LOG_FILE" 2>&1 &

PID=$!
echo $PID > "$PID_FILE"
sleep 2

if kill -0 "$PID" 2>/dev/null; then
    echo "✓ $SERVICE_NAME started (Port: $PORT)"
else
    echo "✗ $SERVICE_NAME failed to start. Check $LOG_FILE"
    exit 1
fi
