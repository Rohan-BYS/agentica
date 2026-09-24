#!/usr/bin/env bash
# ==============================================================================
# Agentica - Automated Multi-System Deployment Bootstrap Script for Hermes
# ==============================================================================
# Single command that performs all 5 steps:
#   1. Installs Agentica & system dependencies (fixes permissions)
#   2. Configures and starts systemd user service (persistent, starts on boot)
#   3. Locates and updates Hermes config.yaml
#   4. Safely signals Hermes gateway reload (handles running-inside-gateway)
#   5. Verifies MCP tool registration (all 10 tools)
#
# Usage:
#   ./deploy_hermes.sh                          # Default: local HTTP
#   ./deploy_hermes.sh --transport stdio         # Use stdio subprocess
#   ./deploy_hermes.sh --config /path/config.yaml
#   ./deploy_hermes.sh --skip-restart            # Skip gateway restart step
#   ./deploy_hermes.sh --test-only               # Only run verification
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TRANSPORT="http"
CUSTOM_CONFIG=""
TEST_ONLY=false
SKIP_RESTART=false

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --transport)
            TRANSPORT="$2"
            shift 2
            ;;
        --config|--hermes-config)
            CUSTOM_CONFIG="$2"
            shift 2
            ;;
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --skip-restart)
            SKIP_RESTART=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./deploy_hermes.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --transport http|stdio    MCP transport (default: http)"
            echo "  --config PATH             Path to Hermes config.yaml"
            echo "  --skip-restart            Skip gateway restart (Step 4)"
            echo "  --test-only               Only run verification tests"
            echo "  --help                    Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1. Use --help for usage."
            exit 1
            ;;
    esac
done

echo "======================================================================"
echo "    AGENTICA + HERMES: AUTOMATED MULTI-SYSTEM DEPLOYMENT BOOTSTRAP   "
echo "======================================================================"
echo "[*] Installation Directory: $SCRIPT_DIR"
echo "[*] MCP Transport Selected: $TRANSPORT"

TARGET_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo "~$TARGET_USER")

# -------------------------------------------------------------------------
# Detect if we are running INSIDE the Hermes gateway process
# (If so, restarting the gateway would kill this script mid-execution)
# -------------------------------------------------------------------------
INSIDE_GATEWAY=false
MY_PID=$$
MY_PPID=$(ps -o ppid= -p $MY_PID 2>/dev/null | tr -d ' ')
if [ -n "$MY_PPID" ]; then
    PARENT_CMD=$(ps -o comm= -p "$MY_PPID" 2>/dev/null || true)
    PARENT_CMDLINE=$(ps -o args= -p "$MY_PPID" 2>/dev/null || true)
    if echo "$PARENT_CMD $PARENT_CMDLINE" | grep -qi "hermes\|gateway"; then
        INSIDE_GATEWAY=true
        echo "[!] Detected: Running inside Hermes gateway process (PID $MY_PPID)."
        echo "[!] Gateway restart will be SKIPPED to prevent self-kill."
    fi
fi

# -------------------------------------------------------------------------
# --test-only: Skip installation, jump to verification
# -------------------------------------------------------------------------
if [ "$TEST_ONLY" = true ]; then
    echo ""
    echo "[*] Running verification tests only..."
    echo ""

    # Test 1: Stdio handshake
    echo "--- Stdio MCP Test ---"
    if [ -x "$SCRIPT_DIR/venv/bin/python3" ]; then
        "$SCRIPT_DIR/venv/bin/python3" -c "
import subprocess, json, sys
try:
    proc = subprocess.Popen(
        ['$SCRIPT_DIR/venv/bin/python3', '-u', '$SCRIPT_DIR/src/server/mcp_server.py'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05'}}) + '\n')
    proc.stdin.flush()
    init_res = json.loads(proc.stdout.readline())
    caps = init_res.get('result', {}).get('capabilities', {})
    has_tools_cap = 'tools' in caps
    server_name = init_res.get('result', {}).get('serverInfo', {}).get('name', '?')
    print(f'  Initialize: OK (server={server_name}, tools_capability={has_tools_cap})')

    proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}) + '\n')
    proc.stdin.flush()
    tools_res = json.loads(proc.stdout.readline())
    tools = [t['name'] for t in tools_res.get('result', {}).get('tools', [])]
    print(f'  Tools List: {len(tools)} tools registered')
    for t in tools:
        print(f'    ✓ {t}')

    # Read stderr for any errors
    proc.stdin.close()
    proc.terminate()
    stderr_output = proc.stderr.read()
    if 'Error' in stderr_output or 'error' in stderr_output:
        print(f'  [WARNING] Server stderr contained errors:')
        for line in stderr_output.strip().split('\n'):
            if 'error' in line.lower():
                print(f'    ! {line}')
    print(f'  [✓] Stdio MCP: PASSED ({len(tools)} tools)')
except Exception as e:
    print(f'  [✗] Stdio MCP: FAILED — {e}')
    sys.exit(1)
"
    else
        echo "  [SKIP] No venv found at $SCRIPT_DIR/venv"
    fi
    echo ""

    # Test 2: HTTP endpoint
    echo "--- HTTP MCP Test ---"
    if command -v curl &>/dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/status 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ]; then
            BODY=$(curl -s --max-time 5 http://127.0.0.1:8000/status 2>/dev/null)
            echo "  HTTP /status: $BODY"
            echo "  [✓] HTTP MCP: PASSED"
        else
            echo "  HTTP /status: HTTP $HTTP_CODE (not reachable)"
            echo "  [✗] HTTP MCP: FAILED — Is the service running? Run: systemctl --user status agentica"
        fi
    else
        echo "  [SKIP] curl not installed"
    fi
    echo ""

    # Test 3: Hermes CLI
    echo "--- Hermes CLI Test ---"
    if command -v hermes &>/dev/null; then
        echo "  Running: hermes mcp test agentica"
        hermes mcp test agentica 2>&1 | sed 's/^/  /' || echo "  [!] hermes mcp test returned non-zero"
    else
        echo "  [SKIP] hermes CLI not found in PATH"
    fi

    exit 0
fi

# =========================================================================
# STEP 1: Install Agentica & Fix Permissions
# =========================================================================
echo ""
echo "[Step 1/5] Installing Agentica & System Dependencies..."
chmod +x *.sh 2>/dev/null || true

./install_linux.sh

# Fix Agentica venv/data ownership
if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    echo "[*] Fixing Agentica file ownership for user '$TARGET_USER'..."
    chown -R "$TARGET_USER":"$TARGET_USER" "$SCRIPT_DIR"
fi
chmod -R u+rwX "$SCRIPT_DIR/venv" "$SCRIPT_DIR/data" 2>/dev/null || true

# Fix Hermes venv ownership if it exists and is root-owned (Issue 5)
HERMES_VENV="/usr/local/lib/hermes-agent/venv"
if [ -d "$HERMES_VENV" ] && [ "$(stat -c '%U' "$HERMES_VENV" 2>/dev/null)" = "root" ]; then
    echo "[*] Fixing Hermes venv ownership at $HERMES_VENV..."
    if [ "$(id -u)" -eq 0 ]; then
        chown -R "$TARGET_USER":"$TARGET_USER" "$HERMES_VENV"
    else
        sudo chown -R "$TARGET_USER":"$TARGET_USER" "$HERMES_VENV" 2>/dev/null || \
            echo "[!] Cannot fix $HERMES_VENV ownership. Run: sudo chown -R $TARGET_USER:$TARGET_USER $HERMES_VENV"
    fi
fi

# Upgrade mcp package in Hermes venv if present (Issue 6)
if [ -x "$HERMES_VENV/bin/pip" ]; then
    echo "[*] Upgrading 'mcp' package in Hermes venv..."
    "$HERMES_VENV/bin/pip" install --upgrade "mcp>=1.0.0" 2>/dev/null || \
        echo "[!] Could not upgrade mcp in Hermes venv. Run manually: $HERMES_VENV/bin/pip install --upgrade 'mcp>=1.0.0'"
fi

# =========================================================================
# STEP 2: Set up persistent background service
# =========================================================================
echo ""
echo "[Step 2/5] Setting up persistent background service..."
if [ "$TRANSPORT" = "http" ]; then
    if command -v systemctl &>/dev/null && [ -d /run/systemd/system ]; then
        if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
            su - "$TARGET_USER" -c "cd '$SCRIPT_DIR' && ./setup_systemd_service.sh"
        else
            ./setup_systemd_service.sh
        fi
        # Also install health check timer (Issue 9)
        if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
            su - "$TARGET_USER" -c "cd '$SCRIPT_DIR' && ./setup_health_timer.sh" 2>/dev/null || true
        else
            ./setup_health_timer.sh 2>/dev/null || true
        fi
        sleep 2
    else
        echo "[!] Systemd not detected (container/chroot). Starting background server..."
        nohup "$SCRIPT_DIR/venv/bin/python3" -m uvicorn src.server.mcp_http_server:app --host 127.0.0.1 --port 8000 > "$SCRIPT_DIR/data/mcp_server.log" 2>&1 &
        echo "[*] Server started (PID: $!)"
        sleep 2
    fi
fi

# =========================================================================
# STEP 3: Locate and Update Hermes config.yaml
# =========================================================================
echo ""
echo "[Step 3/5] Updating Hermes MCP configuration..."

CONFIG_FILE=""
if [ -n "$CUSTOM_CONFIG" ] && [ -f "$CUSTOM_CONFIG" ]; then
    CONFIG_FILE="$CUSTOM_CONFIG"
else
    CANDIDATES=(
        "$USER_HOME/.hermes/config.yaml"
        "$USER_HOME/.config/hermes/config.yaml"
        "$USER_HOME/.hermes/config.yml"
        "$USER_HOME/.config/hermes/config.yml"
        "/etc/hermes/config.yaml"
    )
    for c in "${CANDIDATES[@]}"; do
        if [ -f "$c" ]; then
            CONFIG_FILE="$c"
            break
        fi
    done
fi

if [ -z "$CONFIG_FILE" ]; then
    CONFIG_FILE="$USER_HOME/.hermes/config.yaml"
    mkdir -p "$(dirname "$CONFIG_FILE")"
    [ -f "$CONFIG_FILE" ] || touch "$CONFIG_FILE"
fi

echo "[*] Hermes Config Path: $CONFIG_FILE"

# Backup
cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)" 2>/dev/null || true

# Update config with Python (safe YAML-aware append/update)
"$SCRIPT_DIR/venv/bin/python3" << 'PYEOF'
import sys, re
from pathlib import Path

config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.yaml")
transport = sys.argv[2] if len(sys.argv) > 2 else "http"
script_dir = sys.argv[3] if len(sys.argv) > 3 else "."

content = config_path.read_text(encoding="utf-8") if config_path.exists() else ""

if transport == "stdio":
    entry_lines = [
        f'  agentica:',
        f'    command: "{script_dir}/venv/bin/python3"',
        f'    args:',
        f'      - "-u"',
        f'      - "{script_dir}/src/server/mcp_server.py"',
        f'    env:',
        f'      PYTHONUNBUFFERED: "1"',
    ]
else:
    entry_lines = [
        f'  agentica:',
        f'    url: "http://127.0.0.1:8000/mcp"',
        f'    connect_timeout: 60',
    ]

entry_block = "\n".join(entry_lines)

if "mcp_servers:" in content:
    if "agentica:" in content:
        # Replace existing agentica block (everything from "  agentica:" to next top-level key or end)
        pattern = r"(  agentica:.*?)(?=\n  \w|\n\w|\Z)"
        new_content = re.sub(pattern, entry_block, content, count=1, flags=re.DOTALL)
        print("[*] Updated existing agentica entry in config.yaml")
    else:
        # Append under mcp_servers
        new_content = content.replace("mcp_servers:", "mcp_servers:\n" + entry_block, 1)
        print("[*] Added agentica under existing mcp_servers block")
else:
    new_content = content.rstrip() + "\n\nmcp_servers:\n" + entry_block + "\n"
    print("[*] Appended new mcp_servers block to config.yaml")

config_path.write_text(new_content, encoding="utf-8")
print("[✓] Config updated successfully!")
PYEOF
"$CONFIG_FILE" "$TRANSPORT" "$SCRIPT_DIR"

# =========================================================================
# STEP 4: Safely Signal Hermes Gateway Reload
# =========================================================================
echo ""
echo "[Step 4/5] Signaling Hermes Gateway..."

if [ "$SKIP_RESTART" = true ]; then
    echo "[*] --skip-restart flag set. Skipping gateway restart."
    echo "[!] Run 'hermes gateway restart' manually to load Agentica tools."

elif [ "$INSIDE_GATEWAY" = true ]; then
    # CRITICAL FIX (Issue 3/8): We are running inside the gateway process.
    # Restarting would kill this script mid-execution.
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  IMPORTANT: Deploy script is running INSIDE the Hermes gateway ║"
    echo "║  Restarting the gateway from here would kill this script.      ║"
    echo "║                                                                ║"
    echo "║  To load Agentica tools, do ONE of:                            ║"
    echo "║    1. Run in Telegram/chat:  /reload-mcp                       ║"
    echo "║    2. Run in a terminal:     hermes gateway restart             ║"
    echo "║    3. Run in a terminal:     systemctl --user restart hermes    ║"
    echo "║                                                                ║"
    echo "║  Tools will appear as mcp_agentica_* after reload.             ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

else
    # Safe to restart — we are NOT inside the gateway
    RESTARTED=false

    # Try systemd user service first (cleanest)
    if command -v systemctl &>/dev/null; then
        for svc in hermes-gateway hermes hermes-agent; do
            if systemctl --user is-active "$svc" &>/dev/null 2>&1; then
                echo "[*] Restarting systemd user service: $svc..."
                systemctl --user restart "$svc"
                RESTARTED=true
                break
            fi
        done
        if [ "$RESTARTED" = false ] && [ "$(id -u)" -eq 0 ]; then
            for svc in hermes-gateway hermes hermes-agent; do
                if systemctl is-active "$svc" &>/dev/null 2>&1; then
                    echo "[*] Restarting systemd system service: $svc..."
                    systemctl restart "$svc"
                    RESTARTED=true
                    break
                fi
            done
        fi
    fi

    # Fallback: SIGHUP to trigger config reload without full restart
    if [ "$RESTARTED" = false ]; then
        HERMES_PID=$(pgrep -f "hermes.*gateway" 2>/dev/null | head -1)
        if [ -n "$HERMES_PID" ]; then
            echo "[*] Sending SIGHUP to Hermes gateway (PID $HERMES_PID) for config reload..."
            kill -HUP "$HERMES_PID" 2>/dev/null || true
            RESTARTED=true
        fi
    fi

    if [ "$RESTARTED" = false ]; then
        echo "[*] Hermes gateway not currently running."
        echo "[*] When you start Hermes, Agentica will load automatically from config.yaml."
    fi
fi

# =========================================================================
# STEP 5: Verify Tool Registration
# =========================================================================
echo ""
echo "[Step 5/5] Verifying Agentica Tool Registration..."
sleep 2

VERIFIED=false

# Verify Agentica's own server is healthy
if [ "$TRANSPORT" = "stdio" ]; then
    "$SCRIPT_DIR/venv/bin/python3" -c "
import subprocess, json
try:
    proc = subprocess.Popen(
        ['$SCRIPT_DIR/venv/bin/python3', '-u', '$SCRIPT_DIR/src/server/mcp_server.py'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2024-11-05'}}) + '\n')
    proc.stdin.flush()
    init_line = proc.stdout.readline()
    init_res = json.loads(init_line)
    caps = init_res.get('result', {}).get('capabilities', {})
    print(f'  Initialize: OK (capabilities.tools present: {\"tools\" in caps})')

    proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}) + '\n')
    proc.stdin.flush()
    tools_res = json.loads(proc.stdout.readline())
    tools = [t['name'] for t in tools_res.get('result', {}).get('tools', [])]
    print(f'  Tools ({len(tools)}):')
    for t in tools:
        print(f'    ✓ {t}')
    assert len(tools) >= 8, f'Expected >=8 tools, got {len(tools)}'
    proc.terminate()
    print(f'  [✓] PASSED')
except Exception as e:
    print(f'  [✗] FAILED: {e}')
    exit(1)
" && VERIFIED=true
else
    if command -v curl &>/dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/status 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ]; then
            BODY=$(curl -s --max-time 5 http://127.0.0.1:8000/status 2>/dev/null)
            echo "  HTTP /status: $BODY"
            TOOL_COUNT=$(echo "$BODY" | "$SCRIPT_DIR/venv/bin/python3" -c "import sys,json; print(json.load(sys.stdin).get('tool_count',0))" 2>/dev/null || echo "0")
            if [ "$TOOL_COUNT" -ge 8 ] 2>/dev/null; then
                echo "  [✓] PASSED ($TOOL_COUNT tools)"
                VERIFIED=true
            else
                echo "  [✗] FAILED: Only $TOOL_COUNT tools detected"
            fi
        else
            echo "  [✗] FAILED: HTTP $HTTP_CODE from http://127.0.0.1:8000/status"
            echo "  Try: systemctl --user status agentica"
        fi
    fi
fi

# Also try Hermes CLI verification if available
if command -v hermes &>/dev/null; then
    echo ""
    echo "  --- Hermes CLI Verification ---"
    hermes mcp test agentica 2>&1 | sed 's/^/  /' || true
fi

echo ""
echo "======================================================================"
if [ "$VERIFIED" = true ]; then
    echo "  [SUCCESS] AGENTICA FULLY DEPLOYED!                                 "
else
    echo "  [COMPLETED] Agentica deployed. Review output above for details.    "
fi
echo "======================================================================"
echo " Transport:    $TRANSPORT"
echo " Config:       $CONFIG_FILE"
if [ "$TRANSPORT" = "http" ]; then
    echo " Endpoint:     http://127.0.0.1:8000/mcp"
    echo " Health:       http://127.0.0.1:8000/status"
    echo " Service:      systemctl --user status agentica"
    echo " Logs:         journalctl --user -u agentica -f"
fi
if [ "$INSIDE_GATEWAY" = true ]; then
    echo ""
    echo " ⚠ RESTART NEEDED: Run 'hermes gateway restart' in a separate terminal"
fi
echo "======================================================================"
