# Hermes Agent Configuration Guide for Agentica

This guide details how to configure the **Hermes AI Agent** to connect with Agentica across Linux distributions and multi-system deployments.

---

## Transport Options

Hermes can connect to Agentica using **Local HTTP** (recommended), **Local Stdio**, or **Remote Cloudflare Tunnel**.

---

### Option 1: Local HTTP via Systemd (Recommended for 10+ Linux Systems)

This is the fastest, lowest-latency setup (0ms external network overhead) and starts automatically on boot across any Linux distro.

#### Step 1: Install the systemd user service
```bash
cd ~/agentica
./setup_systemd_service.sh
```

#### Step 2: Configure Hermes `config.yaml`
```yaml
mcp_servers:
  agentica:
    url: "http://127.0.0.1:8000/mcp"
    connect_timeout: 60
```

#### Useful commands:
- Check status: `systemctl --user status agentica`
- View live logs: `journalctl --user -u agentica -f`
- Restart service: `systemctl --user restart agentica`

---

### Option 2: Local Stdio Transport (Direct Subprocess)

Use this if Hermes spawns local subprocesses directly.

> **Note on Stdio Fix**: In previous builds, the `initialize` handshake omitted the `"capabilities": {"tools": {}}` declaration, which caused the Hermes gateway to silently skip tool discovery (`added=[agentica]` without registering tools). This has been resolved, and debug logs are now streamed directly to `stderr` for visibility.

#### Hermes `config.yaml`:

**Direct Python Binary (Most reliable across any shell/working directory):**
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

*Or via the runner script:*
```yaml
mcp_servers:
  agentica:
    command: "/home/YOUR_USER/agentica/run_mcp_stdio.sh"
```

*(Replace `/home/YOUR_USER/agentica` with your actual absolute path).*

---

### Option 3: Remote Transport (Cloudflare Tunnel)

Use this when Hermes runs on a remote server/VM and needs to talk to Agentica running on another machine.

#### Hermes `config.yaml`:
```yaml
mcp_servers:
  agentica:
    url: "https://<YOUR_TUNNEL_URL>/mcp"
    connect_timeout: 120
```

---

## Available Agentica Tools (10 Total)

| Tool | Parameters | Description |
|---|---|---|
| `browse` | `url` (str), `mode` (str: auto/text/struct/visual) | Autonomous navigation with 3-tier escalation |
| `browse_batch` | `urls` (list of str) | Concurrently fetch multiple pages safely |
| `snapshot` | *None* | Get current page AXTree with `@eN` references |
| `click` | `ref` (str: "@e1") | Click interactive element by handle |
| `fill` | `ref` (str), `text` (str) | Type text into input fields by handle |
| `screenshot` | `url` (str) | Capture visual screenshot with base64 data |
| `get_memory_status` | *None* | Inspect RAM safety thresholds |
| `get_human_active_tab` | *None* | Co-browse with human on desktop port 9222 |
| `talk_to_developer` | `message` (str) | Send direct bug report/feedback to Antigravity |
| `get_developer_messages` | *None* | Read dev messages and replies |

---

## Verifying the Connection Manually

To verify stdio handshake on any Linux terminal:
```bash
cd ~/agentica
source venv/bin/activate
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' | python3 -u src/server/mcp_server.py
```
Expected output:
```json
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": false}}, "serverInfo": {"name": "agentica", "version": "1.0.0"}}}
```
