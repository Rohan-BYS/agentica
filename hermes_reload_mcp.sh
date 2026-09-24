#!/usr/bin/env bash
# ==============================================================================
# Agentica - Hermes MCP Reload CLI Helper
# Triggers MCP rediscovery without needing /reload-mcp in Telegram
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================================"
echo "  Agentica — Hermes MCP Reload                                        "
echo "======================================================================"

# -------------------------------------------------------------------------
# 1. Verify Agentica is running first
# -------------------------------------------------------------------------
echo ""
echo "[1/3] Checking Agentica MCP server..."
AGENTICA_OK=false
if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/status 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        BODY=$(curl -s --max-time 5 http://127.0.0.1:8000/status 2>/dev/null)
        echo "  [✓] Agentica healthy: $BODY"
        AGENTICA_OK=true
    else
        echo "  [✗] Agentica not responding (HTTP $HTTP_CODE)"
        # Try to restart
        if command -v systemctl &>/dev/null && systemctl --user is-enabled agentica &>/dev/null 2>&1; then
            echo "  [*] Restarting agentica.service..."
            systemctl --user restart agentica.service
            sleep 2
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/status 2>/dev/null || echo "000")
            if [ "$HTTP_CODE" = "200" ]; then
                echo "  [✓] Agentica recovered after restart"
                AGENTICA_OK=true
            else
                echo "  [✗] Agentica still not responding after restart"
            fi
        fi
    fi
else
    echo "  [!] curl not installed, skipping health check"
fi

# -------------------------------------------------------------------------
# 2. Trigger Hermes gateway reload
# -------------------------------------------------------------------------
echo ""
echo "[2/3] Reloading Hermes gateway..."
RELOADED=false

# Method A: systemd service restart (most reliable)
if command -v systemctl &>/dev/null; then
    for svc in hermes-gateway hermes hermes-agent; do
        if systemctl --user is-active "$svc" &>/dev/null 2>&1; then
            echo "  [*] Restarting systemd user service: $svc..."
            systemctl --user restart "$svc"
            RELOADED=true
            echo "  [✓] Service restarted. MCP discovery will run on startup."
            break
        fi
    done
    # Try system-level services
    if [ "$RELOADED" = false ]; then
        for svc in hermes-gateway hermes hermes-agent; do
            if systemctl is-active "$svc" &>/dev/null 2>&1; then
                echo "  [*] Restarting systemd system service: $svc..."
                sudo systemctl restart "$svc" 2>/dev/null || systemctl restart "$svc" 2>/dev/null || true
                RELOADED=true
                echo "  [✓] System service restarted."
                break
            fi
        done
    fi
fi

# Method B: SIGHUP to running gateway (config reload without full restart)
if [ "$RELOADED" = false ]; then
    HERMES_PID=$(pgrep -f "hermes.*gateway" 2>/dev/null | head -1)
    if [ -n "$HERMES_PID" ]; then
        echo "  [*] Sending SIGHUP to Hermes gateway (PID $HERMES_PID)..."
        kill -HUP "$HERMES_PID" 2>/dev/null || true
        RELOADED=true
        echo "  [✓] SIGHUP sent. Gateway should re-read config."
    fi
fi

# Method C: Hermes CLI (may not exist in this version)
if [ "$RELOADED" = false ] && command -v hermes &>/dev/null; then
    echo "  [*] Trying hermes CLI commands..."
    if hermes mcp reload 2>/dev/null; then
        RELOADED=true
        echo "  [✓] hermes mcp reload succeeded"
    elif hermes gateway restart 2>/dev/null; then
        RELOADED=true
        echo "  [✓] hermes gateway restart succeeded"
    else
        echo "  [!] hermes CLI commands not available in this version"
    fi
fi

if [ "$RELOADED" = false ]; then
    echo "  [!] Could not reload Hermes automatically."
    echo "  Manual options:"
    echo "    • Type /reload-mcp in Telegram chat"
    echo "    • Run: hermes gateway restart"
    echo "    • Run: systemctl --user restart hermes"
fi

# -------------------------------------------------------------------------
# 3. Post-reload verification
# -------------------------------------------------------------------------
echo ""
echo "[3/3] Post-reload verification..."
sleep 3

if command -v hermes &>/dev/null; then
    echo "  Running: hermes mcp test agentica"
    hermes mcp test agentica 2>&1 | sed 's/^/  /' || echo "  [!] hermes mcp test not available"
fi

if [ "$AGENTICA_OK" = true ]; then
    echo ""
    echo "  Quick verify: curl http://127.0.0.1:8000/status"
    curl -s http://127.0.0.1:8000/status 2>/dev/null | sed 's/^/  /' || true
fi

echo ""
echo "======================================================================"
echo "  Done. If tools don't appear, try: /reload-mcp in Telegram"
echo "======================================================================"
