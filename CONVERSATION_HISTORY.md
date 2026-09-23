# Agentica Browser — Project History & Conversation Archive

> **Session Reference**: [Agentica Build & Architecture Session](conversation://a6a3d878-a344-46f4-9528-988022276cde)  
> **Conversation ID**: `a6a3d878-a344-46f4-9528-988022276cde`  
> **Workspace**: `C:\Users\U1\Desktop\ai-browser-workspace\ai-browser`

---

## 1. Project Genesis & Vision
The user set out to build an **AI-native web browser ("Agentica")** designed primarily for autonomous AI agents (over Model Context Protocol / MCP) and secondarily for human co-browsing and daily research on lightweight hardware (specifically 8GB RAM Linux/Windows machines).

### Core Constraints & Principles:
- **Strict RAM Ceiling**: System memory consumption must **never exceed 90%** (preserving at least 10% for OS, mouse cursor, and Remote Desktop responsiveness).
- **Primary User = AI Agent**: Built for massive concurrent research (100–500 pages) without crashing the machine.
- **Secondary User = Human**: Capable of being launched as a standard visible browser with an address bar, tabs, and full video playback (YouTube), while maintaining strict profile isolation between human and agent.
- **Co-Browsing Bridge**: Allows a human to open any tab and instruct the AI to inspect, summarize, or interact with that live tab over port `9222`.

---

## 2. Best-of-All-Worlds Architecture (Synthesized Repositories)
The engine synthesized the key algorithms from 5 leading open-source projects into a single unified Python engine:

| Source Repository | Technology / Concept | Incorporated Feature in Agentica |
| :--- | :--- | :--- |
| **`browser-use`** | Python CDP Automation | Centroid-based smart clicking, occlusion detection (`elementFromPoint`), React-safe form filling. |
| **`agent-browser` (Vercel)** | Rust/TS Accessibility Control | Dynamic Accessibility Tree (`AXTree`) extraction, self-healing `@eN` references (`RefMap`). |
| **`browser39`** | Rust Token Compiler | Token-efficient HTML-to-Markdown compiler, anti-prompt-injection (bidi override stripping), link array compaction. |
| **`lightpanda`** | Zig Headless Browser | Minimal CSS selector generator (`SelectorPath`), single-execution JSON schema data extraction. |
| **`moli`** | Rust Memory-Safe Browser | Adaptive concurrency throttling, process tracking, emergency GC. |

---

## 3. The 3-Tier Dynamic Routing (TDR) Engine
1. **Tier 1 (Text Engine — `tier1_text.py`)**:
   - Pure async HTTP (`httpx`) + HTML-to-Markdown parsing (`BeautifulSoup`, `trafilatura`).
   - Zero Chromium processes = **0 MB GPU/Renderer RAM**.
   - Crawls 50–100 URLs in seconds with negligible memory footprint.
2. **Tier 2 (Structural Engine — `tier2_struct.py`)**:
   - Headless Chromium with resource blocking (all images, CSS, fonts, and media aborted).
   - Generates compact `@eN` Accessibility Tree for actions (click, fill, navigate).
   - Memory footprint: only ~50MB–80MB per tab.
3. **Tier 3 (Visual Engine — `tier3_visual.py`)**:
   - Full Chromium with screenshot rendering, PIL-based bounding box overlays, and schema extraction.

---

## 4. Hardware Optimization & Tab Hibernation
- **`MemoryManager` (`memory_manager.py`)**: Enforces an 85% safety threshold and 88% emergency garbage collection, dynamically adjusting concurrent tasks.
- **`ProcessManager` (`process_manager.py`)**: Implements low-level Windows Job Objects (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) via `ctypes` to ensure zero orphaned Chromium processes if Python closes.
- **`TabHibernator` (`tab_hibernator.py`)**: Virtual Tab Pool that keeps a maximum of 5 active tabs in RAM. Excess tabs are serialized to fast NVMe storage (`data/hibernate/`) and their render processes terminated (0 MB RAM). Tabs are reconstituted in <150ms on demand.

---

## 5. Live Co-Browsing Tool (`get_human_active_tab`)
- Launched on `--remote-debugging-port=9222` with persistent profile `data/profiles/human`.
- MCP tool allows an AI agent to attach to the human's open window, read page text, title, and URL in <0.3s, and return summaries without closing or interfering with the user's active window.
- Verified on real-world sites (e.g., live extraction and 130-page forensic audit of `https://www.bys.marketing/`).

---

## 6. Branding & Windows Shell Integration
- **Custom Minimalist Logo**: Black-and-white stylized 'A' with an integrated eye, converted to multi-resolution Windows Icon (`agentica.ico`: 16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256).
- **Binary Deep Patching (`deep_patch.py`)**: Replaces hardcoded Google strings in `agentica.exe`, `chrome.dll`, and `en-US.pak` so Windows Task Manager and titlebars natively display **Agentica**.
- **Direct Shortcut Binding**: Desktop and Start Menu shortcuts point directly to `agentica.exe` with arguments, ensuring Taskbar pinning keeps the custom name and icon intact.
- **Inno Setup Installer (`installer.iss`)**: Generates a ~2MB setup wizard (`Agentica_Setup_v1.0.exe`) with an official uninstaller and smart dependency setup (`setup_dependencies.ps1`).

---

## 7. How to Continue in Antigravity IDE
1. Open **Antigravity IDE**.
2. Select **File > Open Folder** and choose `C:\Users\U1\Desktop\ai-browser-workspace\ai-browser`.
3. In the chat panel / sessions list, click on this session:  
   👉 **[Agentica Build & Architecture Session](conversation://a6a3d878-a344-46f4-9528-988022276cde)**  
4. All messages, tool executions, code files, and context will be immediately accessible!
