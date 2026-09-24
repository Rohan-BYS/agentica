#!/usr/bin/env bash
# ==============================================================================
# Agentica - Hermes MCP Reload CLI Helper
# Triggers MCP rediscovery without needing to manually restart the terminal
# ==============================================================================
set -e

echo "[*] Triggering Hermes MCP reload..."

RELOADED=false

# 1. Try systemd user services
if command -v systemctl &>/dev/null; then
    for svc in hermes-gateway hermes hermes-agent; do
        if systemctl --user is-active "$svc" &>/dev/null; then
            echo "[*] Restarting systemd user service: $svc..."
            systemctl --user restart "$svc"
            RELOADED=true
            break
        fi
    done
fi

# 2. Try Hermes CLI
if command -v hermes &>/dev/null; then
    echo "[*] Invoking 'hermes mcp reload'..."
    hermes mcp reload 2>/dev/null || hermes gateway restart 2>/dev/null || true
    RELOADED=true
fi

# 3. Try SIGHUP signal to hermes process
if [ "$RELOADED" = false ] && pgrep -f "hermes" &>/dev/null; then
    echo "[*] Sending SIGHUP to hermes processes..."
    pkill -HUP -f "hermes" 2>/dev/null || true
    RELOADED=true
fi

echo "[*] Verifying Agentica MCP endpoint status..."
if command -v curl &>/dev/null; then
    curl -s http://127.0.0.1:8000/status || echo "[!] Local HTTP endpoint not reachable on port 8000."
fi

echo ""
echo "[✓] MCP Reload command executed."
