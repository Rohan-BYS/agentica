#!/usr/bin/env bash
# ==============================================================================
# Agentica - Systemd Health Check Timer Installer
# Checks Agentica MCP service health every 5 minutes.
# Auto-restarts if down. Reports status to data/health.log.
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${USER}"
USER_HOME=$(eval echo "~$TARGET_USER")
SERVICE_DIR="$USER_HOME/.config/systemd/user"

echo "[*] Setting up Agentica health check timer..."

mkdir -p "$SERVICE_DIR"

# 1. Health check script
HEALTH_SCRIPT="$SCRIPT_DIR/health_check.sh"
cat <<'HEALTHEOF' > "$HEALTH_SCRIPT"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/data/health.log"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
mkdir -p "$SCRIPT_DIR/data"

check_http() {
    if command -v curl &>/dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/status 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ]; then
            TOOLS=$(curl -s --max-time 5 http://127.0.0.1:8000/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_count',0))" 2>/dev/null || echo "?")
            echo "$TIMESTAMP [HEALTHY] HTTP 200 — $TOOLS tools active" >> "$LOG"
            return 0
        fi
    fi
    return 1
}

if ! check_http; then
    echo "$TIMESTAMP [DOWN] Agentica HTTP not responding. Attempting restart..." >> "$LOG"
    if command -v systemctl &>/dev/null; then
        systemctl --user restart agentica.service 2>/dev/null || true
        sleep 3
        if check_http; then
            echo "$TIMESTAMP [RECOVERED] Agentica restarted successfully" >> "$LOG"
        else
            echo "$TIMESTAMP [FAILED] Agentica restart did not recover service" >> "$LOG"
        fi
    fi
fi

# Trim log to last 500 lines
if [ -f "$LOG" ]; then
    tail -500 "$LOG" > "${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
fi
HEALTHEOF
chmod +x "$HEALTH_SCRIPT"

# 2. Systemd service unit (oneshot, triggered by timer)
cat <<EOF > "$SERVICE_DIR/agentica-health.service"
[Unit]
Description=Agentica MCP Health Check

[Service]
Type=oneshot
ExecStart=$HEALTH_SCRIPT
EOF

# 3. Systemd timer unit (every 5 minutes)
cat <<EOF > "$SERVICE_DIR/agentica-health.timer"
[Unit]
Description=Agentica MCP Health Check Timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s

[Install]
WantedBy=timers.target
EOF

# 4. Enable timer
systemctl --user daemon-reload
systemctl --user enable --now agentica-health.timer

echo ""
echo "[✓] Health check timer installed!"
echo "    - Checks every 5 minutes"
echo "    - Auto-restarts Agentica if down"
echo "    - Logs to: $SCRIPT_DIR/data/health.log"
echo "    - Timer status: systemctl --user status agentica-health.timer"
