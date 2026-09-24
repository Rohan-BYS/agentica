#!/usr/bin/env bash
# ==============================================================================
# Agentica - Systemd User Service Installer for Linux
# Runs Agentica MCP HTTP Server as a persistent background service on 127.0.0.1:8000
# Ideal for Hermes & multi-system deployments (zero latency, no cloudflare tunnel needed)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${USER}"
USER_HOME=$(eval echo "~$TARGET_USER")
SERVICE_DIR="$USER_HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/agentica.service"

echo "[*] Setting up Agentica systemd user service..."

# 1. Ensure venv exists
if [ ! -x "$SCRIPT_DIR/venv/bin/python3" ]; then
    echo "[x] Error: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "    Please run ./install_linux.sh first."
    exit 1
fi

# 2. Create systemd user service directory
mkdir -p "$SERVICE_DIR"

# 3. Write unit file
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Agentica AI Browser MCP Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/venv/bin/python3 -m uvicorn src.server.mcp_http_server:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
Environment="PYTHONPATH=$SCRIPT_DIR"
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=default.target
EOF

# 4. Reload and enable service
echo "[*] Enabling and starting agentica.service..."
systemctl --user daemon-reload
systemctl --user enable agentica.service
systemctl --user restart agentica.service

# 5. Enable lingering so the service stays running even if user logs out
if command -v loginctl &>/dev/null; then
    loginctl enable-linger "$TARGET_USER" 2>/dev/null || true
fi

echo ""
echo "======================================================================"
echo " [✓] Agentica MCP HTTP Service is now RUNNING in the background!"
echo "======================================================================"
echo " - Local URL:      http://127.0.0.1:8000/mcp"
echo " - SSE URL:        http://127.0.0.1:8000/sse"
echo " - Service Status: systemctl --user status agentica"
echo " - Live Logs:      journalctl --user -u agentica -f"
echo " - Stop Service:   systemctl --user stop agentica"
echo " - Restart:        systemctl --user restart agentica"
echo "======================================================================"
