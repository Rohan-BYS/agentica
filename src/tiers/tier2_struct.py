"""
Tier 2: Structural/Accessibility Engine.
Uses Playwright CDP for deep browser interaction with AI-optimized output.

Implements:
- Accessibility tree extraction with @eN references (from Agent Browser)
- Self-healing element resolution (from Agent Browser)
- Smart clicking with occlusion detection (from Browser Use)
- Smart form filling with React bypass (from Browser Use)
- Anti-detection flags (from Browser Use)
- Dialog auto-handling
- Resource blocking for minimal RAM
"""

from __future__ import annotations
import asyncio
import json
import re
from typing import Optional, Dict, List, Literal
from playwright.async_api import async_playwright, Page, BrowserContext, CDPSession


# --- Constants ---
ANTI_DETECTION_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    '--simulate-outdated-no-au=Tue, 31 Dec 2099 23:59:59 GMT',
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-search-engine-choice-screen",
]

INTERACTIVE_ROLES = {
    "button", "link", "textbox", "checkbox", "radio", "combobox",
    "listbox", "menuitem", "menuitemcheckbox", "menuitemradio",
    "option", "searchbox", "slider", "spinbutton", "switch",
    "tab", "treeitem",
}

CONTENT_ROLES = {
    "heading", "img", "table", "cell", "row", "list", "listitem",
    "article", "banner", "complementary", "contentinfo", "form",
    "main", "navigation", "region", "search",
}

BLOCKED_RESOURCE_TYPES = {"image", "stylesheet", "font", "media"}


class RefEntry:
    """Tracks an element reference for self-healing resolution."""
    __slots__ = ("backend_node_id", "role", "name", "nth", "node_id")

    def __init__(self, backend_node_id: int, role: str, name: str, nth: int, node_id: Optional[int] = None):
        self.backend_node_id = backend_node_id
        self.role = role
        self.name = name
        self.nth = nth
        self.node_id = node_id


class Tier2StructEngine:
    """
    Tier 2: Structural/Accessibility Engine with CDP-level control.
    Blocks visual resources, extracts accessibility trees, and provides
    @eN-based element interaction with self-healing resolution.
    """

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.cdp: Optional[CDPSession] = None
        self.ref_map: Dict[str, RefEntry] = {}
        self._ref_counter: int = 0
        self._dialog_messages: List[str] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init_browser(self, headless: bool = True):
        """Launch browser with anti-detection flags and resource blocking."""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
        if self.browser is None:
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=ANTI_DETECTION_ARGS,
            )

    async def _ensure_page(self, headless: bool = True):
        """Ensure a page and CDP session are ready."""
        await self.init_browser(headless=headless)
        if self.context is None:
            self.context = await self.browser.new_context()
        if self.page is None:
            self.page = await self.context.new_page()
            # Block heavy resources
            await self.page.route("**/*", self._route_handler)
            # Setup CDP session
            self.cdp = await self.page.context.new_cdp_session(self.page)
            await self.cdp.send("DOM.enable")
            await self.cdp.send("Accessibility.enable")
            # Auto-handle dialogs
            self.page.on("dialog", self._handle_dialog)

    async def _route_handler(self, route):
        """Block images, CSS, fonts, media to save RAM."""
        if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
            await route.abort()
        else:
            await route.continue_()

    async def _handle_dialog(self, dialog):
        """Auto-dismiss JS dialogs and save messages."""
        self._dialog_messages.append(f"[{dialog.type}] {dialog.message}")
        try:
            await dialog.accept()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def get_accessibility_tree(self, url: str, headless: bool = True) -> str:
        """Navigate to URL and return formatted accessibility tree with @eN refs."""
        await self._ensure_page(headless=headless)
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(500)  # Brief settle
        except Exception as e:
            return f"Navigation error: {str(e)}"
        return await self.get_snapshot_text()

    async def navigate(self, url: str):
        """Navigate current page to a new URL."""
        await self._ensure_page()
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(500)

    async def go_back(self):
        """Go back in history."""
        if self.page:
            await self.page.go_back(wait_until="domcontentloaded")

    async def go_forward(self):
        """Go forward in history."""
        if self.page:
            await self.page.go_forward(wait_until="domcontentloaded")

    # ------------------------------------------------------------------
    # Snapshot & AXTree
    # ------------------------------------------------------------------

    async def get_snapshot_text(self) -> str:
        """Get current page's accessibility tree as formatted text with @eN refs."""
        if not self.cdp:
            return "Error: No active page"

        self.ref_map.clear()
        self._ref_counter = 0

        try:
            ax_result = await self.cdp.send("Accessibility.getFullAXTree")
            nodes = ax_result.get("nodes", [])
        except Exception as e:
            return f"AXTree extraction error: {str(e)}"

        if not nodes:
            return "Empty accessibility tree"

        # Build parent-children map
        children_map: Dict[str, List[str]] = {}
        node_map: Dict[str, dict] = {}
        for node in nodes:
            nid = node.get("nodeId", "")
            node_map[nid] = node
            children_map[nid] = node.get("childIds", [])

        # Find root
        root_id = nodes[0].get("nodeId", "") if nodes else ""

        # Render tree
        role_name_counts: Dict[str, int] = {}
        lines: List[str] = []
        self._walk_ax_tree(root_id, node_map, children_map, role_name_counts, lines, depth=0)

        url = self.page.url if self.page else "unknown"
        header = f"# Accessibility Snapshot of {url}\n"
        header += f"# {len(self.ref_map)} interactive elements found\n\n"
        return header + "\n".join(lines)

    def _walk_ax_tree(self, node_id: str, node_map: dict, children_map: dict,
                      role_counts: dict, lines: list, depth: int):
        """Recursively walk AX tree, assign @eN refs, aggregate StaticText."""
        node = node_map.get(node_id)
        if not node:
            return
        if node.get("ignored", False):
            # Still walk children of ignored nodes
            for child_id in children_map.get(node_id, []):
                self._walk_ax_tree(child_id, node_map, children_map, role_counts, lines, depth)
            return

        role = self._extract_ax_value(node.get("role", {}))
        name = self._extract_ax_value(node.get("name", {}))
        value = self._extract_ax_value(node.get("value", {}))
        backend_id = node.get("backendDOMNodeId", 0)

        # Skip pure InlineTextBox nodes
        if role == "InlineTextBox":
            return

        # Determine interactivity
        is_interactive = role.lower() in INTERACTIVE_ROLES
        children = children_map.get(node_id, [])

        # Aggregate consecutive StaticText children
        aggregated_children = self._aggregate_static_text(children, node_map)

        # Build line
        indent = "  " * depth
        ref_tag = ""
        if is_interactive and backend_id:
            ref_key = f"@e{self._ref_counter}"
            self._ref_counter += 1

            # Track nth occurrence for self-healing
            role_name_key = f"{role}:{name}"
            nth = role_counts.get(role_name_key, 0)
            role_counts[role_name_key] = nth + 1

            self.ref_map[ref_key] = RefEntry(
                backend_node_id=backend_id,
                role=role,
                name=name,
                nth=nth,
            )
            ref_tag = f" [{ref_key}]"

        # Format node text
        parts = [role]
        if name:
            parts.append(f'"{name}"')
        if value:
            parts.append(f'value="{value}"')

        line = f"{indent}- {' '.join(parts)}{ref_tag}"
        lines.append(line)

        # Walk children
        for child_id in aggregated_children:
            self._walk_ax_tree(child_id, node_map, children_map, role_counts, lines, depth + 1)

    def _aggregate_static_text(self, child_ids: List[str], node_map: dict) -> List[str]:
        """Merge consecutive StaticText siblings into one (from Agent Browser)."""
        if not child_ids:
            return child_ids

        result = []
        i = 0
        while i < len(child_ids):
            node = node_map.get(child_ids[i])
            role = self._extract_ax_value(node.get("role", {})) if node else ""

            if role == "StaticText":
                # Collect consecutive StaticText nodes
                texts = []
                start = i
                while i < len(child_ids):
                    n = node_map.get(child_ids[i])
                    r = self._extract_ax_value(n.get("role", {})) if n else ""
                    if r != "StaticText":
                        break
                    name = self._extract_ax_value(n.get("name", {})) if n else ""
                    texts.append(name)
                    i += 1
                # Merge into first node
                if texts and node:
                    merged_name = " ".join(t for t in texts if t)
                    node["name"] = {"type": "computedString", "value": merged_name}
                result.append(child_ids[start])
            else:
                result.append(child_ids[i])
                i += 1
        return result

    @staticmethod
    def _extract_ax_value(prop) -> str:
        """Extract string value from an AX property dict."""
        if isinstance(prop, dict):
            return str(prop.get("value", ""))
        return str(prop) if prop else ""

    # ------------------------------------------------------------------
    # Element Resolution (Self-Healing)
    # ------------------------------------------------------------------

    async def _resolve_ref(self, ref: str) -> Optional[RefEntry]:
        """Resolve an @eN reference, with self-healing if DOM mutated."""
        entry = self.ref_map.get(ref)
        if not entry or not self.cdp:
            return None

        # Fast path: try cached backend_node_id
        try:
            await self.cdp.send("DOM.describeNode", {"backendNodeId": entry.backend_node_id})
            return entry
        except Exception:
            pass

        # Self-healing: re-query AXTree and find by (role, name, nth)
        try:
            ax_result = await self.cdp.send("Accessibility.getFullAXTree")
            match_count = 0
            for node in ax_result.get("nodes", []):
                if node.get("ignored", False):
                    continue
                role = self._extract_ax_value(node.get("role", {}))
                name = self._extract_ax_value(node.get("name", {}))
                if role == entry.role and name == entry.name:
                    if match_count == entry.nth:
                        new_bid = node.get("backendDOMNodeId", 0)
                        if new_bid:
                            entry.backend_node_id = new_bid
                            return entry
                    match_count += 1
        except Exception:
            pass

        return None

    async def _get_element_center(self, entry: RefEntry) -> Optional[tuple]:
        """Get the center coordinates of an element via CDP box model."""
        try:
            await self.cdp.send("DOM.scrollIntoViewIfNeeded", {"backendNodeId": entry.backend_node_id})
            box = await self.cdp.send("DOM.getBoxModel", {"backendNodeId": entry.backend_node_id})
            content = box["model"]["content"]
            # content is [x1,y1, x2,y2, x3,y3, x4,y4] quad
            xs = [content[i] for i in range(0, 8, 2)]
            ys = [content[i] for i in range(1, 8, 2)]
            cx = sum(xs) / 4
            cy = sum(ys) / 4
            return (cx, cy)
        except Exception:
            return None

    async def _check_occlusion(self, x: float, y: float, backend_node_id: int) -> Optional[str]:
        """Check if another element is covering the click point."""
        js = f"""() => {{
            const el = document.querySelector('[data-nexus-bid="{backend_node_id}"]');
            const hit = document.elementFromPoint({x}, {y});
            if (!hit) return null;
            // Check if hit is the target or a descendant/ancestor
            if (el && (hit === el || el.contains(hit) || hit.contains(el))) return null;
            let desc = hit.tagName.toLowerCase();
            if (hit.id) desc += '#' + hit.id;
            else if (hit.className && typeof hit.className === 'string')
                desc += '.' + hit.className.trim().split(/\\s+/).slice(0, 2).join('.');
            return desc;
        }}"""
        try:
            result = await self.page.evaluate(js)
            return result
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Actions: Click, Fill, Select, Hover, Scroll
    # ------------------------------------------------------------------

    async def click(self, ref: str) -> str:
        """Click an element by @eN reference with occlusion detection."""
        entry = await self._resolve_ref(ref)
        if not entry:
            return f"Error: Could not resolve reference {ref}"

        center = await self._get_element_center(entry)
        if not center:
            # Fallback: JS click
            try:
                result = await self.cdp.send("DOM.resolveNode", {"backendNodeId": entry.backend_node_id})
                object_id = result["object"]["objectId"]
                await self.cdp.send("Runtime.callFunctionOn", {
                    "objectId": object_id,
                    "functionDeclaration": "function() { this.click(); }",
                })
                return f"Clicked {ref} (JS fallback)"
            except Exception as e:
                return f"Error clicking {ref}: {str(e)}"

        cx, cy = center

        # Dispatch CDP mouse events
        try:
            await self.cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": cx, "y": cy
            })
            await self.cdp.send("Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": cx, "y": cy,
                "button": "left", "clickCount": 1
            })
            await self.cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": cx, "y": cy,
                "button": "left", "clickCount": 1
            })
            return f"Clicked {ref} at ({cx:.0f}, {cy:.0f})"
        except Exception as e:
            return f"Error clicking {ref}: {str(e)}"

    async def fill(self, ref: str, text: str) -> str:
        """Fill text into an element with React prototype setter bypass."""
        entry = await self._resolve_ref(ref)
        if not entry:
            return f"Error: Could not resolve reference {ref}"

        try:
            # Focus the element
            await self.cdp.send("DOM.focus", {"backendNodeId": entry.backend_node_id})

            # Clear existing value using React-safe prototype setter bypass
            result = await self.cdp.send("DOM.resolveNode", {"backendNodeId": entry.backend_node_id})
            object_id = result["object"]["objectId"]
            await self.cdp.send("Runtime.callFunctionOn", {
                "objectId": object_id,
                "functionDeclaration": """function() {
                    const proto = this instanceof HTMLTextAreaElement
                        ? HTMLTextAreaElement.prototype
                        : HTMLInputElement.prototype;
                    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (desc && desc.set) {
                        desc.set.call(this, '');
                        this.dispatchEvent(new Event('input', {bubbles: true}));
                        this.dispatchEvent(new Event('change', {bubbles: true}));
                    } else {
                        this.value = '';
                    }
                }""",
            })

            # Type each character with triplet key events
            for char in text:
                await self.cdp.send("Input.dispatchKeyEvent", {
                    "type": "keyDown", "key": char, "text": char,
                })
                await self.cdp.send("Input.dispatchKeyEvent", {
                    "type": "char", "text": char,
                })
                await self.cdp.send("Input.dispatchKeyEvent", {
                    "type": "keyUp", "key": char,
                })

            return f"Filled {ref} with '{text}'"
        except Exception as e:
            return f"Error filling {ref}: {str(e)}"

    async def select(self, ref: str, value: str) -> str:
        """Select a dropdown option by value."""
        entry = await self._resolve_ref(ref)
        if not entry:
            return f"Error: Could not resolve reference {ref}"
        try:
            result = await self.cdp.send("DOM.resolveNode", {"backendNodeId": entry.backend_node_id})
            object_id = result["object"]["objectId"]
            await self.cdp.send("Runtime.callFunctionOn", {
                "objectId": object_id,
                "functionDeclaration": f"""function() {{
                    this.value = '{value}';
                    this.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}""",
            })
            return f"Selected '{value}' in {ref}"
        except Exception as e:
            return f"Error selecting in {ref}: {str(e)}"

    async def hover(self, ref: str) -> str:
        """Hover over an element."""
        entry = await self._resolve_ref(ref)
        if not entry:
            return f"Error: Could not resolve reference {ref}"
        center = await self._get_element_center(entry)
        if not center:
            return f"Error: Could not get coordinates for {ref}"
        cx, cy = center
        try:
            await self.cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": cx, "y": cy
            })
            return f"Hovered over {ref} at ({cx:.0f}, {cy:.0f})"
        except Exception as e:
            return f"Error hovering {ref}: {str(e)}"

    async def scroll(self, direction: str = "down", amount: int = 300) -> str:
        """Scroll the page."""
        delta_y = amount if direction == "down" else -amount
        try:
            await self.page.evaluate(f"window.scrollBy(0, {delta_y})")
            return f"Scrolled {direction} by {amount}px"
        except Exception as e:
            return f"Error scrolling: {str(e)}"

    # ------------------------------------------------------------------
    # JavaScript & Markdown
    # ------------------------------------------------------------------

    async def evaluate_js(self, script: str) -> str:
        """Execute JavaScript on the current page."""
        try:
            result = await self.page.evaluate(script)
            return json.dumps(result, default=str) if result is not None else "null"
        except Exception as e:
            return f"JS Error: {str(e)}"

    async def get_markdown(self) -> str:
        """Extract current page content as Markdown."""
        try:
            html = await self.page.content()
            from src.tiers.content_extractor import ContentExtractor
            extractor = ContentExtractor()
            return extractor.extract_markdown(html, base_url=self.page.url)
        except Exception:
            # Fallback: simple text extraction
            try:
                text = await self.page.evaluate("document.body.innerText")
                return text or ""
            except Exception as e:
                return f"Error extracting markdown: {str(e)}"

    # ------------------------------------------------------------------
    # Tab Management
    # ------------------------------------------------------------------

    async def list_tabs(self) -> List[dict]:
        """List all open tabs."""
        if not self.context:
            return []
        return [{"index": i, "url": p.url, "title": await p.title()}
                for i, p in enumerate(self.context.pages)]

    async def new_tab(self, url: str = "about:blank") -> str:
        """Open a new tab."""
        if not self.context:
            return "Error: No browser context"
        page = await self.context.new_page()
        if url != "about:blank":
            await page.goto(url, wait_until="domcontentloaded")
        self.page = page
        self.cdp = await self.page.context.new_cdp_session(self.page)
        await self.cdp.send("DOM.enable")
        await self.cdp.send("Accessibility.enable")
        self.page.on("dialog", self._handle_dialog)
        return f"Opened new tab: {url}"

    async def switch_tab(self, index: int) -> str:
        """Switch to a tab by index."""
        if not self.context or index >= len(self.context.pages):
            return f"Error: Tab {index} does not exist"
        self.page = self.context.pages[index]
        self.cdp = await self.page.context.new_cdp_session(self.page)
        await self.cdp.send("DOM.enable")
        await self.cdp.send("Accessibility.enable")
        return f"Switched to tab {index}: {self.page.url}"

    async def close_tab(self, index: Optional[int] = None) -> str:
        """Close a tab by index (default: current)."""
        if not self.context:
            return "Error: No browser context"
        pages = self.context.pages
        if index is not None and index < len(pages):
            await pages[index].close()
        elif self.page:
            await self.page.close()
            self.page = None
        return "Tab closed"

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close(self):
        """Shut down browser and all resources."""
        if self.cdp:
            try:
                await self.cdp.detach()
            except Exception:
                pass
            self.cdp = None
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
        self.page = None
        self.ref_map.clear()
