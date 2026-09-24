#!/usr/bin/env bash
# ==============================================================================
# Agentica - MCP Stdio Runner for AI Agents (Hermes, Claude, etc.)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Determine python executable
if [ -x "$SCRIPT_DIR/venv/bin/python3" ]; then
    PY_BIN="$SCRIPT_DIR/venv/bin/python3"
elif [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
    PY_BIN="$SCRIPT_DIR/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PY_BIN="$(command -v python3)"
else
    >&2 echo "[Agentica MCP Error] python3 not found. Please run ./install_linux.sh first."
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR"
export PYTHONUNBUFFERED=1

exec "$PY_BIN" -u "$SCRIPT_DIR/src/server/mcp_server.py"
