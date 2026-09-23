#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
export PYTHONPATH="$SCRIPT_DIR"
exec python3 -u src/server/mcp_server.py
