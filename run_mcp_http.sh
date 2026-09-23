#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
export PYTHONPATH="$SCRIPT_DIR"
exec python3 -m uvicorn src.server.mcp_http_server:app --host 0.0.0.0 --port 8000
