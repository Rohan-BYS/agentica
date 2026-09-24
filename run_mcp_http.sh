#!/usr/bin/env bash
# ==============================================================================
# Agentica - MCP HTTP / SSE Server Runner
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -x "$SCRIPT_DIR/venv/bin/python3" ]; then
    PY_BIN="$SCRIPT_DIR/venv/bin/python3"
elif [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
    PY_BIN="$SCRIPT_DIR/venv/bin/python"
else
    PY_BIN="python3"
fi

export PYTHONPATH="$SCRIPT_DIR"
export PYTHONUNBUFFERED=1

exec "$PY_BIN" -m uvicorn src.server.mcp_http_server:app --host 0.0.0.0 --port 8000
