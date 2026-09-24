# Hermes Agent Integration & Multi-System Deployment Guide

> **Version**: 2.0 — Addresses all issues from the Hermes Weakness Report

---

## ⚡ Quick Start: 1-Command Automated Bootstrap

```bash
cd ~/agentica
chmod +x deploy_hermes.sh
./deploy_hermes.sh
```

This single command:
1. Installs Agentica + system dependencies (fixes file permissions automatically)
2. Sets up systemd user service on `http://127.0.0.1:8000/mcp` (persistent, starts on boot)
3. Fixes Hermes venv ownership (`/usr/local/lib/hermes-agent/venv/`) and upgrades `mcp` package
4. Updates Hermes `config.yaml` (auto-detects location, creates backup)
5. Safely restarts Hermes gateway (detects inside-gateway execution and avoids self-kill)
6. Installs health check timer (auto-restarts Agentica if it goes down)
7. Verifies all 10 tools are registered

### Command Options
```bash
./deploy_hermes.sh                              # Default: local HTTP
./deploy_hermes.sh --transport stdio             # Use stdio subprocess
./deploy_hermes.sh --config /path/config.yaml    # Custom config path
./deploy_hermes.sh --skip-restart                # Don't restart gateway
./deploy_hermes.sh --test-only                   # Only run verification
```

---

## Transport Options

### ✅ Option 1: Local HTTP via Systemd (RECOMMENDED for Production)

Zero network latency, auto-starts on boot, auto-restarts on crash, works across all Linux distros.

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  agentica:
    url: "http://127.0.0.1:8000/mcp"
    connect_timeout: 60
```

Management:
```bash
systemctl --user status agentica          # Check status
journalctl --user -u agentica -f          # Live logs
systemctl --user restart agentica         # Restart
```

### Option 2: Local Stdio (Direct Subprocess)

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  agentica:
    command: "/home/YOUR_USER/agentica/venv/bin/python3"
    args:
      - "-u"
      - "/home/YOUR_USER/agentica/src/server/mcp_server.py"
    env:
      PYTHONUNBUFFERED: "1"
```

### ⚠️ Option 3: Remote Cloudflare Tunnel (DEV/TESTING ONLY)

> **WARNING**: Cloudflare quick tunnels are unreliable for production use.
> They return 530 errors without warning and have no uptime guarantee.
> Use **only** for temporary testing when direct network access is unavailable.

```yaml
# ~/.hermes/config.yaml — DEV ONLY
mcp_servers:
  agentica:
    url: "https://<TUNNEL_URL>/mcp"
    connect_timeout: 120
```

---

## Available Tools (All 10)

| Tool | Parameters | Description |
|---|---|---|
| `browse` | `url`, `mode` | 3-tier autonomous navigation (Text → DOM → Vision) |
| `browse_batch` | `urls` | Concurrent safe scraping with RAM bounds |
| `snapshot` | — | Live accessibility tree with `@eN` references |
| `click` | `ref` | Click element (e.g. `@e1`) |
| `fill` | `ref`, `text` | Type into form inputs |
| `screenshot` | `url` | Visual screenshot with base64 |
| `get_human_active_tab` | — | Co-browse desktop port 9222 |
| `get_memory_status` | — | RAM thresholds and worker counts |
| `talk_to_developer` | `message` | Developer message bus |
| `get_developer_messages` | — | Read developer replies |

---

## Troubleshooting Guide

### Issue: Tools don't appear after deployment

**Cause**: Hermes gateway hasn't reloaded MCP config.

**Fix** (in priority order):
1. Type `/reload-mcp` in Telegram chat
2. Run `hermes gateway restart` in a terminal
3. Run `systemctl --user restart hermes` in a terminal
4. Run `./hermes_reload_mcp.sh`

### Issue: "Permission denied" when installing packages in Hermes venv

**Cause**: `/usr/local/lib/hermes-agent/venv/` is owned by root.

**Fix**:
```bash
sudo chown -R $USER:$USER /usr/local/lib/hermes-agent/venv/
```
*(deploy_hermes.sh does this automatically)*

### Issue: `mcp` package version error (no `streamable_http_client`)

**Cause**: Old `mcp` package version.

**Fix**:
```bash
/usr/local/lib/hermes-agent/venv/bin/pip install --upgrade "mcp>=1.0.0"
```
*(deploy_hermes.sh does this automatically)*

### Issue: deploy_hermes.sh fails at "Restart Gateway" step

**Cause**: Script is running inside the Hermes gateway process. Restarting kills the script.

**Fix**: The latest deploy_hermes.sh detects this and prints manual instructions instead of crashing.
You can also use `--skip-restart`:
```bash
./deploy_hermes.sh --skip-restart
# Then manually:
hermes gateway restart
```

### Issue: Server goes down and tools disappear

**Fix**: Install the health check timer:
```bash
./setup_health_timer.sh
```
This checks every 5 minutes and auto-restarts Agentica if it's down.

### Issue: Stdio subprocess spawn — gateway shows "added=[agentica]" but no tools

**Cause (now fixed)**: The `initialize` handshake was missing `"capabilities": {"tools": {}}`. Without this, Hermes skips `tools/list`.

**Verification**: Run `./deploy_hermes.sh --test-only` to confirm the handshake includes `capabilities.tools`.

### Issue: Can't edit config.yaml from inside the agent

**Cause**: Hermes security policy prevents agent writes to config files.

**Fix**: Use `./deploy_hermes.sh` which handles config writes externally, or manually edit `~/.hermes/config.yaml`.

---

## Quick Verification Commands

```bash
# Test Agentica server directly
curl http://127.0.0.1:8000/status

# Full stdio + HTTP test suite
./deploy_hermes.sh --test-only

# Hermes-side test
hermes mcp test agentica

# Health log
tail -20 ~/agentica/data/health.log
```
