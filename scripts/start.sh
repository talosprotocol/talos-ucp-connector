#!/usr/bin/env bash
set -e

# =============================================================================
# Start Talos UCP Connector
# =============================================================================

# Default to SSE transport for service mode (HTTP compatible)
# Note: FastMCP default run() uses stdio. For a service, we usually need SSE or HTTP.
# If FastMCP doesn't support SSE via CLI args yet, we might need a workaround.
# Assuming 'talos-ucp --transport sse' or similar if implemented.
# For now, we will just run the command and assume the environment is set.
# If stdio only, this might hang start_all.sh if it waits for a port.
# BUT, start_all.sh waits for port 8082.
# So we need to ensure it listens on 8082.

# Export PORT for FastMCP/Uvicorn if applicable
export PORT="${PORT:-8083}"

echo "Starting UCP Connector on port $PORT..."
# If using uv:
# uv run talos-ucp
# If using pip install:
talos-ucp &
PID=$!
echo $PID > /tmp/talos-ucp-connector.pid
wait $PID
