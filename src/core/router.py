"""
Nexus Browser: Smart Router & Controller.
Routes requests to the optimal engine tier with auto-escalation,
adaptive concurrency, and memory-safe batch processing.
"""

import asyncio
from typing import Literal, List, Optional, Dict, Any
from src.tiers.tier1_text import Tier1TextEngine
from src.tiers.tier2_struct import Tier2StructEngine
from src.tiers.tier3_visual import Tier3VisualEngine
from src.core.memory_manager import MemoryManager
from src.core.auto_escalation import AutoEscalation
from src.core.secret_manager import SecretManager
from src.core.session_manager import SessionManager


class AIBrowserRouter:
    """
    The Nexus Browser Controller.
    Routes requests to the appropriate engine tier based on AI needs.
    Features:
    - Auto-escalation from text → structural → visual
    - Adaptive concurrency based on RAM usage
    - Secret redaction for LLM safety
    - Cookie/session sharing across tiers
    """

    def __init__(self, ram_threshold: float = 85.0):
        self.tier1 = Tier1TextEngine()
        self.tier2 = Tier2StructEngine()
        self.tier3 = Tier3VisualEngine()
        self.memory = MemoryManager(threshold_percent=ram_threshold)
        self.escalation = AutoEscalation()
        self.secrets = SecretManager()
        self.sessions = SessionManager()

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    async def browse(
        self,
        url: str,
        mode: Literal["auto", "text", "struct", "visual"] = "auto",
        show_human_ui: bool = False,
        redact_secrets: bool = True,
    ) -> Dict[str, Any]:
        """
        Main entry point for browsing a single URL.

        Args:
            url: The URL to browse.
            mode: Engine tier selection ("auto" lets the router decide).
            show_human_ui: If True, run Chromium with visible window.
            redact_secrets: If True, replace sensitive tokens with handles.

        Returns:
            Dict with url, mode_used, content, and optional visual_assets.
        """
        await self.memory.wait_for_memory()

        # Synchronize cookies from Tier 2 into Tier 1 so authenticated sessions persist across browse()
        if self.tier2.context:
            try:
                cookies = await self.tier2.context.cookies()
                for c in cookies:
                    domain = c.get("domain", "").lstrip(".")
                    if domain:
                        self.tier1.client.cookies.set(
                            c["name"],
                            c["value"],
                            domain=domain,
                            path=c.get("path", "/")
                        )
            except Exception:
                pass

        if mode == "text" or mode == "auto":
            result = await self.tier1.fetch(url)

            if mode == "auto":
                # Check if we need to escalate
                escalation_tier, reason = self.escalation.should_escalate(
                    html=result, headers={}
                )
                if escalation_tier == "tier2":
                    mode = "struct"
                elif escalation_tier == "tier3":
                    mode = "visual"
                else:
                    content = result
                    if redact_secrets:
                        content = self.secrets.redact(content)

                    # Retrieve visual content detected during extraction
                    visual_assets = list(self.tier1.visual_sentinel.visual_assets.values())

                    return {
                        "url": url,
                        "mode_used": "text",
                        "content": content,
                        "visual_assets": visual_assets if visual_assets else None,
                    }
            else:
                content = result
                if redact_secrets:
                    content = self.secrets.redact(content)
                return {"url": url, "mode_used": "text", "content": content}

        if mode == "struct":
            result = await self.tier2.get_accessibility_tree(url, headless=not show_human_ui)
            if redact_secrets:
                result = self.secrets.redact(result)
            return {"url": url, "mode_used": "struct", "content": result}

        if mode == "visual":
            result = await self.tier3.capture_screenshot(url, headless=not show_human_ui)
            return {"url": url, "mode_used": "visual", "content": result}

        return {"url": url, "mode_used": mode, "content": "Unknown mode"}

    async def browse_batch(
        self,
        urls: List[str],
        max_concurrency: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process a massive list of URLs concurrently using Tier 1 (text).
        Concurrency adapts to current RAM usage.

        Args:
            urls: List of URLs to fetch.
            max_concurrency: Override max concurrent requests (default: adaptive).

        Returns:
            List of result dicts.
        """
        # Adaptive concurrency based on RAM
        if max_concurrency is None:
            max_concurrency = self.memory.get_allowed_concurrency()

        semaphore = asyncio.Semaphore(max_concurrency)

        async def fetch_with_sem(url: str) -> Dict[str, Any]:
            async with semaphore:
                await self.memory.wait_for_memory()
                try:
                    return await self.browse(url, mode="text")
                except Exception as e:
                    return {"url": url, "mode_used": "text", "content": f"Error: {str(e)}"}

        tasks = [fetch_with_sem(u) for u in urls]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # Tier 2 Direct Actions (for interactive browsing)
    # ------------------------------------------------------------------

    async def snapshot(self) -> str:
        """Get current page accessibility tree with @eN references."""
        return await self.tier2.get_snapshot_text()

    async def click(self, ref: str) -> str:
        """Click an element by @eN reference."""
        return await self.tier2.click(ref)

    async def fill(self, ref: str, text: str) -> str:
        """Fill text into an element by @eN reference."""
        resolved_text = self.secrets.resolve(text)
        return await self.tier2.fill(ref, resolved_text)

    async def select_option(self, ref: str, value: str) -> str:
        """Select a dropdown option."""
        return await self.tier2.select(ref, value)

    async def hover(self, ref: str) -> str:
        """Hover over an element."""
        return await self.tier2.hover(ref)

    async def scroll(self, direction: str = "down", amount: int = 300) -> str:
        """Scroll the page."""
        return await self.tier2.scroll(direction, amount)

    async def navigate(self, url: str) -> str:
        """Navigate to a URL in current Tier 2 session."""
        await self.tier2.navigate(url)
        return f"Navigated to {url}"

    async def go_back(self) -> str:
        """Go back in browser history."""
        await self.tier2.go_back()
        return "Went back"

    async def go_forward(self) -> str:
        """Go forward in browser history."""
        await self.tier2.go_forward()
        return "Went forward"

    async def evaluate_js(self, script: str) -> str:
        """Execute JavaScript on current page."""
        return await self.tier2.evaluate_js(script)

    async def list_tabs(self) -> List[dict]:
        """List all open tabs."""
        return await self.tier2.list_tabs()

    async def new_tab(self, url: str = "about:blank") -> str:
        """Open a new tab."""
        return await self.tier2.new_tab(url)

    async def switch_tab(self, index: int) -> str:
        """Switch to a tab by index."""
        return await self.tier2.switch_tab(index)

    async def close_tab(self, index: Optional[int] = None) -> str:
        """Close a tab."""
        return await self.tier2.close_tab(index)

    # ------------------------------------------------------------------
    # Tier 3 Direct Actions (for visual inspection)
    # ------------------------------------------------------------------

    async def screenshot(self, url: Optional[str] = None, headless: bool = True) -> Dict:
        """Take a screenshot."""
        if url:
            cookies = None
            if self.tier2.context:
                try:
                    cookies = await self.tier2.context.cookies()
                except Exception:
                    pass
            return await self.tier3.capture_screenshot(url, headless=headless, cookies=cookies)
        return {"error": "URL required for screenshot"}

    async def screenshot_element(self, url: str, selector: str, headless: bool = True) -> Dict:
        """Capture a specific element screenshot."""
        return await self.tier3.capture_element(url, selector, headless=headless)

    async def extract_structured_data(self, url: str) -> Dict:
        """Extract JSON-LD, OpenGraph, Twitter Cards."""
        return await self.tier3.extract_structured_data(url)

    async def generate_pdf(self, url: str) -> Dict:
        """Generate PDF of a page."""
        return await self.tier3.generate_pdf(url)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    async def get_memory_status(self) -> Dict:
        """Get current memory status."""
        return {
            "ram_percent": self.memory.get_usage_percent(),
            "threshold": self.memory.threshold_percent,
            "allowed_concurrency": self.memory.get_allowed_concurrency(),
            "is_safe": self.memory.is_memory_available(),
        }

    async def get_cookies(self, domain: Optional[str] = None) -> List[dict]:
        """Get cookies, optionally filtered by domain."""
        return self.sessions.get_cookies(domain)

    async def set_cookies(self, cookies: List[dict]):
        """Set cookies."""
        self.sessions.set_cookies(cookies)

    async def get_human_active_tab(self) -> Dict[str, Any]:
        """
        Connects over CDP to port 9222 (the Human browser profile)
        and reads the active tab's URL, Title, and content for the AI to summarize.
        """
        import httpx
        from playwright.async_api import async_playwright
        
        # Check if human browser is running on port 9222
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("http://127.0.0.1:9222/json/version", timeout=1.5)
                if res.status_code != 200:
                    return {"status": "error", "message": "Agentica Human Browser is not running on port 9222."}
        except Exception:
            return {"status": "error", "message": "Agentica Human Browser is not currently open. Please open it from your desktop first."}
            
        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                contexts = browser.contexts
                if not contexts or not contexts[0].pages:
                    return {"status": "error", "message": "No tabs currently open in Agentica."}
                    
                pages = contexts[0].pages
                active_page = pages[-1]  # Most recent active tab
                
                url = active_page.url
                title = await active_page.title()
                
                # Extract text content from the active tab
                content = await active_page.evaluate("""() => {
                    // Extract main readable content
                    const main = document.querySelector('main, article, #content') || document.body;
                    return main ? main.innerText : document.body.innerText;
                }""")
                
                # Disconnect cleanly without closing the user's browser window
                await browser.close()
                
                return {
                    "status": "success",
                    "url": url,
                    "title": title,
                    "content": content[:8000],  # Return up to 8000 chars for clean LLM summary
                    "total_length": len(content)
                }
        except Exception as e:
            return {"status": "error", "message": f"Failed to inspect human tab: {str(e)}"}

    async def shutdown(self):
        """Gracefully shutdown all engines."""
        await self.tier1.close()
        await self.tier2.close()
        await self.tier3.close()
