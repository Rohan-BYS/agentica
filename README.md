# 🌐 Agentica Browser

**The Dual-Mode AI-First Browser Engine & Model Context Protocol (MCP) Gateway**

Agentica is a lightweight, resource-conscious browser designed for **AI Agents** as primary operators and **Humans** as secondary co-browsers. It eliminates the standard failure modes of web browsing for AI (context window overflow, memory crashes, 403 bot blocks, and fragile element selectors) by treating the web as a structured semantic information pipeline rather than a visual canvas.

---

## ⚡ Highlights

- **3-Tier Adaptive Routing**:
  - **Tier 1 (Text Engine)**: Sub-second HTTP text and metadata extraction with zero Chromium overhead (<60MB RAM for 150 sites).
  - **Tier 2 (Structural AXTree Engine)**: Headless Chromium generating semantic Accessibility Trees with stable element handles (`@e1`, `@e2`). Click and fill inputs without CSS selectors or pixel guessing.
  - **Tier 3 (Visual Engine)**: On-demand full-page screenshots, element crops, and PDF generation.
- **Auto-Escalation**: Automatically escalates from lightweight text parsing to stealth Playwright Chromium when JavaScript single-page apps or bot challenges are detected.
- **Hardware-Safe Concurrency**: Adaptive concurrency governed by real-time RAM telemetry. Inactive tabs hibernate to NVMe disk storage with full session/localStorage preservation.
- **Human Co-Browsing**: Live Chrome DevTools Protocol (CDP) bridge on port 9222 allows an AI agent to inspect and summarize what the human user is reading on their screen without interrupting them.
- **Standard MCP Protocol**: Native support for stdio and HTTP/SSE JSON-RPC transports. Works seamlessly with Hermes, Claude Desktop, Cursor, or any MCP client.

---

## 🚀 Quick Start (Debian 13 / Ubuntu / Linux)

### 1. Clone & Install
```bash
git clone https://github.com/<your-username>/agentica.git
cd agentica
chmod +x install_linux.sh
./install_linux.sh
```

The installer will:
- Set up a clean Python virtual environment (`venv`)
- Install dependencies from `requirements.txt`
- Install Playwright Chromium along with all necessary OS library dependencies (`playwright install --with-deps chromium`)

### 2. Run MCP for Local Agents (Hermes)
For agents running on the same Linux machine over standard input/output (stdio):
```bash
./run_mcp_stdio.sh
```

**Agent MCP Configuration (`config.json`):**
```json
{
  "mcpServers": {
    "agentica": {
      "command": "/path/to/agentica/run_mcp_stdio.sh"
    }
  }
}
```

### 3. Run MCP as an HTTP / SSE Server (Optional)
If you want to access the browser over the local network or internet:
```bash
./run_mcp_http.sh
```
Listens on `http://0.0.0.0:8000` with:
- SSE endpoint: `/sse`
- Direct JSON-RPC: `/mcp`

---

## 🛠️ MCP Tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `browse` | `url` (str), `mode` ("auto" \| "text" \| "struct" \| "visual") | Fetch and extract clean semantic markdown/text. |
| `browse_batch`| `urls` (list of str) | Concurrently fetch multiple URLs in parallel with RAM guards. |
| `snapshot` | *None* | Get current page AXTree with interactive `@eN` references. |
| `click` | `ref` (str, e.g. `@e1`) | Click an element by its stable handle. |
| `fill` | `ref` (str), `text` (str) | Type into a search box or form input. |
| `screenshot` | `url` (str) | Capture a full screenshot (returns both `file_path` and `image_base64`). |
| `get_human_active_tab` | *None* | Inspect what the human is browsing on port 9222. |
| `get_memory_status` | *None* | Query current RAM usage and safe concurrency limits. |

---

## 🧪 Interactive Form Testing (Example)

Hermes or any agent can interact with web pages using stable references:

```python
# 1. Open interactive page
call_agentica("browse", url="https://duckduckgo.com", mode="struct")

# 2. Inspect element tree
tree = call_agentica("snapshot")
# Output: [Searchbox: "Search with DuckDuckGo"] @e1

# 3. Type search query
call_agentica("fill", ref="@e1", text="Agentica Browser")

# 4. Click search button
call_agentica("click", ref="@e2")
```

---

## 📄 License
MIT License. Open source and built for the autonomous agent ecosystem.
