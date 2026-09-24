# Hermes Agent Integration & Multi-System Deployment Guide

This guide details how to automatically deploy and connect **Agentica AI Browser** with **Hermes AI Agent** across 10+ Linux systems (Debian, Ubuntu, Fedora, Arch, CentOS, etc.).

---

## ⚡ Quick Start: 1-Command Automated Bootstrap

To deploy Agentica, configure Hermes, start the background service, and verify tool registration across any Linux machine:

```bash
cd ~/agentica
chmod +x deploy_hermes.sh
./deploy_hermes.sh
```

### What this single command does automatically:
1. **Installs Agentica** and OS library dependencies with root/user permissions handled cleanly.
2. **Sets up systemd user service** (`agentica.service`) on `http://127.0.0.1:8000/mcp` (starts on boot, auto-restarts on crash, 0ms network latency).
3. **Updates Hermes `config.yaml`** (locates `~/.hermes/config.yaml` or custom path and inserts/updates the `agentica` MCP block).
4. **Restarts the Hermes Gateway** cleanly.
5. **Verifies tool registration** (ensures all 10 tools are active and responding).

---

## Manual Configuration Options

If you prefer manual configuration, Hermes can connect via **Local HTTP** (recommended) or **Local Stdio**.

### Option 1: Local HTTP (Recommended for Multi-System Rollouts)

No external network dependencies, no tunnel latency, and persistent across terminal exits.

#### 1. Enable Systemd Service
```bash
./setup_systemd_service.sh
```

#### 2. Configure `~/.hermes/config.yaml`
```yaml
mcp_servers:
  agentica:
    url: "http://127.0.0.1:8000/mcp"
    connect_timeout: 60
```

#### 3. Management Commands
- Service Status: `systemctl --user status agentica`
- Live Logs: `journalctl --user -u agentica -f`
- Restart Server: `systemctl --user restart agentica`
- Reload Hermes MCP: `./hermes_reload_mcp.sh`

---

### Option 2: Local Stdio (Direct Subprocess)

#### Configure `~/.hermes/config.yaml`
```yaml
mcp_servers:
  agentica:
    command: "/home/YOUR_USER/agentica/venv/bin/python3"
    args:
      - "-u"
      - "/home/YOUR_USER/agentica/src/server/mcp_server.py"
    env:
      PYTHONUNBUFFERED: "1"
```

*(Or use `/home/YOUR_USER/agentica/run_mcp_stdio.sh`)*

---

## Available Agentica Tools (All 10 Registered)

| Tool | Parameters | Description |
|---|---|---|
| `browse` | `url` (str), `mode` (str) | Autonomous navigation with 3-tier escalation (Text/DOM/Vision) |
| `browse_batch` | `urls` (list) | Concurrent safe scraping with RAM bounds |
| `snapshot` | *None* | Live accessibility tree with clickable `@eN` references |
| `click` | `ref` (str) | Click element handle (e.g. `@e1`) |
| `fill` | `ref` (str), `text` (str) | Type text into forms / input fields |
| `screenshot` | `url` (str) | Capture visual screenshot with base64 data |
| `get_human_active_tab` | *None* | Co-browse on desktop port 9222 with human user |
| `get_memory_status` | *None* | Real-time RAM thresholds and safe worker counts |
| `talk_to_developer` | `message` (str) | Direct developer message bus |
| `get_developer_messages` | *None* | Read developer replies and notifications |

---

## Troubleshooting & Key Fixes

### 1. Stdio Tool Discovery Issue (Resolved)
- **Symptom**: Gateway showed `MCP servers reconciled: added=[agentica]`, but zero tools appeared.
- **Cause**: The `initialize` JSON-RPC handshake returned `"capabilities": {}`. Under the MCP 2024-11-05 spec, if `"capabilities.tools"` is missing, the client assumes the server has no tools and skips `tools/list`.
- **Fix**: Declared `"capabilities": {"tools": {"listChanged": false}}` and added logging to `sys.stderr` so logs show in Hermes gateway.

### 2. HTTP Server Stopped After Terminal Exit (Resolved)
- **Cause**: Running uvicorn in a terminal session terminates with SIGHUP when the shell closes.
- **Fix**: Run `./setup_systemd_service.sh` to run Agentica as a user systemd daemon (`systemctl --user enable --now agentica`).

### 3. Venv Permissions on Fresh Installs (Resolved)
- **Cause**: Cloning or running installer with `sudo` made `venv/` owned by `root`.
- **Fix**: Installer automatically detects `$SUDO_USER` and sets ownership to the regular user with `chown -R "$TARGET_USER"`.

### 4. Triggering MCP Discovery Without Full Gateway Restart
- Run `./hermes_reload_mcp.sh` to trigger discovery on the running gateway.
