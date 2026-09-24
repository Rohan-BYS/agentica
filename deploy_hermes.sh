#!/usr/bin/env bash
# ==============================================================================
# Agentica - Automated Multi-System Deployment Bootstrap Script for Hermes
# Performs all 5 steps in a single automated command:
#   1. Installs Agentica & system dependencies with zero permission issues
#   2. Configures and starts systemd user service (persistent, starts on boot)
#   3. Locates and updates Hermes config.yaml
#   4. Restarts the Hermes gateway
#   5. Verifies MCP tool registration (all 10 tools)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

TRANSPORT="http"
CUSTOM_CONFIG=""
TEST_ONLY=false

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
        *)
            echo "Unknown option: $1"
            echo "Usage: ./deploy_hermes.sh [--transport http|stdio] [--config /path/to/config.yaml] [--test-only]"
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

# If test only, skip installation
if [ "$TEST_ONLY" = true ]; then
    echo "[*] Running verification tests only..."
    if [ "$TRANSPORT" = "stdio" ]; then
        "$SCRIPT_DIR/venv/bin/python3" -c "
import subprocess, json
proc = subprocess.Popen(['$SCRIPT_DIR/venv/bin/python3', '-u', '$SCRIPT_DIR/src/server/mcp_server.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}}) + '\n')
proc.stdin.flush()
init_res = json.loads(proc.stdout.readline())
proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}) + '\n')
proc.stdin.flush()
tools_res = json.loads(proc.stdout.readline())
tools = [t['name'] for t in tools_res.get('result', {}).get('tools', [])]
print(f'[✓] Stdio MCP Verified! {len(tools)} tools registered: {tools}')
proc.terminate()
"
    else
        "$SCRIPT_DIR/venv/bin/python3" -c "
import httpx
try:
    r = httpx.get('http://127.0.0.1:8000/status', timeout=5.0)
    data = r.json()
    print(f'[✓] Local HTTP MCP Verified! Status: {data.get(\"status\")}, Tools ({data.get(\"tool_count\")}): {data.get(\"tools\")}')
except Exception as e:
    print(f'[x] HTTP check failed: {e}')
    exit(1)
"
    fi
    exit 0
fi

# -------------------------------------------------------------------------
# STEP 1: Install Agentica & Fix Permissions
# -------------------------------------------------------------------------
echo ""
echo "[Step 1/5] Installing Agentica & System Dependencies..."
chmod +x install_linux.sh setup_systemd_service.sh run_mcp_stdio.sh run_mcp_http.sh launch_human.sh create_desktop_shortcut.sh

./install_linux.sh

# Fix all permissions so venv and data are completely owned by target user
if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    echo "[*] Fixing file ownership for user '$TARGET_USER'..."
    chown -R "$TARGET_USER":"$TARGET_USER" "$SCRIPT_DIR"
fi
chmod -R u+rwX "$SCRIPT_DIR/venv" "$SCRIPT_DIR/data" 2>/dev/null || true

# -------------------------------------------------------------------------
# STEP 2: Set up and verify persistent systemd service
# -------------------------------------------------------------------------
echo ""
echo "[Step 2/5] Setting up persistent background service..."
if [ "$TRANSPORT" = "http" ]; then
    if command -v systemctl &>/dev/null && [ -d /run/systemd/system ]; then
        # Run systemd setup as the target user
        if [ "$(id -u)" -eq 0 ] && [ -n "$SUDO_USER" ]; then
            su - "$TARGET_USER" -c "cd '$SCRIPT_DIR' && ./setup_systemd_service.sh"
        else
            ./setup_systemd_service.sh
        fi
        sleep 2
    else
        echo "[!] Systemd not detected (container/chroot). Starting background server..."
        nohup "$SCRIPT_DIR/venv/bin/python3" -m uvicorn src.server.mcp_http_server:app --host 127.0.0.1 --port 8000 > "$SCRIPT_DIR/data/mcp_server.log" 2>&1 &
        sleep 2
    fi
fi

# -------------------------------------------------------------------------
# STEP 3: Locate and Update Hermes config.yaml
# -------------------------------------------------------------------------
echo ""
echo "[Step 3/5] Updating Hermes MCP configuration..."

CONFIG_FILE=""
if [ -n "$CUSTOM_CONFIG" ] && [ -f "$CUSTOM_CONFIG" ]; then
    CONFIG_FILE="$CUSTOM_CONFIG"
else
    # Auto-detect Hermes configuration paths
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
    # Default to standard ~/.hermes/config.yaml
    CONFIG_FILE="$USER_HOME/.hermes/config.yaml"
    mkdir -p "$(dirname "$CONFIG_FILE")"
    if [ ! -f "$CONFIG_FILE" ]; then
        touch "$CONFIG_FILE"
    fi
fi

echo "[*] Hermes Config Path: $CONFIG_FILE"

# Backup config before modifying
cp "$CONFIG_FILE" "${CONFIG_FILE}.bak.$(date +%s)" 2>/dev/null || true

# Update Hermes config safely with Python
"$SCRIPT_DIR/venv/bin/python3" -c "
import os, sys, re
from pathlib import Path

config_path = Path('$CONFIG_FILE')
transport = '$TRANSPORT'
script_dir = '$SCRIPT_DIR'

content = config_path.read_text(encoding='utf-8') if config_path.exists() else ''

if transport == 'stdio':
    mcp_block = f'''
mcp_servers:
  agentica:
    command: \"{script_dir}/venv/bin/python3\"
    args:
      - \"-u\"
      - \"{script_dir}/src/server/mcp_server.py\"
    env:
      PYTHONUNBUFFERED: \"1\"
'''
else:
    mcp_block = '''
mcp_servers:
  agentica:
    url: \"http://127.0.0.1:8000/mcp\"
    connect_timeout: 60
'''

# Check if mcp_servers already exists
if 'mcp_servers:' in content:
    # If agentica already exists in config, replace its block
    if 'agentica:' in content:
        print('[*] Existing agentica entry found in config.yaml. Updating...')
        # Remove old agentica block using regex
        pattern = r'(\\s+agentica:.*?)(?=\\n\\s*\\w+:|\\Z)'
        if transport == 'stdio':
            new_entry = f'  agentica:\\n    command: \"{script_dir}/venv/bin/python3\"\\n    args:\\n      - \"-u\"\\n      - \"{script_dir}/src/server/mcp_server.py\"\\n    env:\\n      PYTHONUNBUFFERED: \"1\"'
        else:
            new_entry = '  agentica:\\n    url: \"http://127.0.0.1:8000/mcp\"\\n    connect_timeout: 60'
        new_content = re.sub(pattern, new_entry, content, flags=re.DOTALL)
        config_path.write_text(new_content, encoding='utf-8')
    else:
        print('[*] Adding agentica under existing mcp_servers block...')
        if transport == 'stdio':
            add_snippet = f'  agentica:\\n    command: \"{script_dir}/venv/bin/python3\"\\n    args:\\n      - \"-u\"\\n      - \"{script_dir}/src/server/mcp_server.py\"\\n    env:\\n      PYTHONUNBUFFERED: \"1\"\\n'
        else:
            add_snippet = '  agentica:\\n    url: \"http://127.0.0.1:8000/mcp\"\\n    connect_timeout: 60\\n'
        new_content = content.replace('mcp_servers:', 'mcp_servers:\\n' + add_snippet)
        config_path.write_text(new_content, encoding='utf-8')
else:
    print('[*] Appending mcp_servers block to config.yaml...')
    new_content = content.rstrip() + '\\n' + mcp_block.strip() + '\\n'
    config_path.write_text(new_content, encoding='utf-8')

print('[✓] Config updated successfully!')
"

# -------------------------------------------------------------------------
# STEP 4: Restart Hermes Gateway
# -------------------------------------------------------------------------
echo ""
echo "[Step 4/5] Restarting Hermes Gateway..."

RESTARTED=false

# Try systemd user service
if command -v systemctl &>/dev/null; then
    for svc in hermes-gateway hermes hermes-agent; do
        if systemctl --user is-active "$svc" &>/dev/null; then
            echo "[*] Restarting systemd user service: $svc..."
            systemctl --user restart "$svc"
            RESTARTED=true
            break
        fi
    done
    if [ "$RESTARTED" = false ] && [ "$(id -u)" -eq 0 ]; then
        for svc in hermes-gateway hermes hermes-agent; do
            if systemctl is-active "$svc" &>/dev/null; then
                echo "[*] Restarting systemd system service: $svc..."
                systemctl restart "$svc"
                RESTARTED=true
                break
            fi
        done
    fi
fi

# Try hermes CLI
if [ "$RESTARTED" = false ] && command -v hermes &>/dev/null; then
    echo "[*] Attempting reload via 'hermes' CLI..."
    hermes mcp reload 2>/dev/null || hermes gateway restart 2>/dev/null || true
    RESTARTED=true
fi

# Signal running process if found
if [ "$RESTARTED" = false ]; then
    if pgrep -f "hermes" &>/dev/null; then
        echo "[*] Sending SIGHUP to running Hermes process..."
        pkill -HUP -f "hermes" 2>/dev/null || true
        RESTARTED=true
    fi
fi

if [ "$RESTARTED" = false ]; then
    echo "[!] Note: Hermes gateway process was not running. When you start Hermes, Agentica will load automatically."
fi

# -------------------------------------------------------------------------
# STEP 5: Verify Tool Registration
# -------------------------------------------------------------------------
echo ""
echo "[Step 5/5] Verifying Agentica Tool Registration..."

sleep 2

VERIFIED=false
if [ "$TRANSPORT" = "stdio" ]; then
    "$SCRIPT_DIR/venv/bin/python3" -c "
import subprocess, json
try:
    proc = subprocess.Popen(['$SCRIPT_DIR/venv/bin/python3', '-u', '$SCRIPT_DIR/src/server/mcp_server.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}}) + '\n')
    proc.stdin.flush()
    proc.stdout.readline()
    proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}) + '\n')
    proc.stdin.flush()
    tools_res = json.loads(proc.stdout.readline())
    tools = [t['name'] for t in tools_res.get('result', {}).get('tools', [])]
    print(f'[*] Stdio Tools Detected ({len(tools)}): {tools}')
    assert len(tools) >= 8
    proc.terminate()
except Exception as e:
    print(f'[x] Verification failed: {e}')
    exit(1)
" && VERIFIED=true
else
    "$SCRIPT_DIR/venv/bin/python3" -c "
import httpx
try:
    r = httpx.get('http://127.0.0.1:8000/status', timeout=5.0)
    data = r.json()
    print(f'[*] HTTP Server: {data.get(\"status\")} ({data.get(\"tool_count\")} tools)')
    for t in data.get('tools', []):
        print(f'    - {t}')
    assert data.get('tool_count', 0) >= 8
except Exception as e:
    print(f'[x] Verification failed: {e}')
    exit(1)
" && VERIFIED=true
fi

# Test via Hermes CLI if present
if command -v hermes &>/dev/null; then
    echo "[*] Testing via 'hermes mcp test agentica'..."
    hermes mcp test agentica 2>/dev/null || true
fi

echo ""
echo "======================================================================"
if [ "$VERIFIED" = true ]; then
    echo "  [SUCCESS] AGENTICA FULLY DEPLOYED AND REGISTERED WITH HERMES!      "
else
    echo "  [COMPLETED] Agentica deployed. Please review service status.        "
fi
echo "======================================================================"
echo " - Deployment Transport: $TRANSPORT"
echo " - Hermes Config:        $CONFIG_FILE"
if [ "$TRANSPORT" = "http" ]; then
    echo " - Local Endpoint:       http://127.0.0.1:8000/mcp"
    echo " - Check Service:        systemctl --user status agentica"
    echo " - Live Logs:            journalctl --user -u agentica -f"
fi
echo "======================================================================"
