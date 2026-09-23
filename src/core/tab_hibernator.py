import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import Page, BrowserContext

class VirtualTab:
    def __init__(self, tab_id: int, url: str):
        self.tab_id = tab_id
        self.url = url
        self.status = "hot"  # "hot" (in RAM) or "cold" (on NVMe)
        self.last_accessed = time.time()
        self.page: Optional[Page] = None
        self.hibernate_path = Path(f"data/hibernate/tab_{tab_id}.json")

class TabHibernator:
    """
    Manages a Virtual Tab Pool.
    Keeps a maximum number of 'hot' tabs in RAM.
    Serializes 'cold' tabs to fast NVMe storage to save RAM.
    """
    def __init__(self, max_hot_tabs: int = 5):
        self.max_hot_tabs = max_hot_tabs
        self.tabs: Dict[int, VirtualTab] = {}
        self._next_id = 0
        
        # Ensure hibernation directory exists
        Path("data/hibernate").mkdir(parents=True, exist_ok=True)

    async def create_tab(self, context: BrowserContext, url: str = "about:blank") -> VirtualTab:
        """Create a new tab, hibernating oldest if we hit the limit."""
        await self._enforce_limits()
        
        tab_id = self._next_id
        self._next_id += 1
        
        vtab = VirtualTab(tab_id, url)
        vtab.page = await context.new_page()
        if url != "about:blank":
            await vtab.page.goto(url, wait_until="domcontentloaded")
            
        self.tabs[tab_id] = vtab
        return vtab

    async def get_page(self, context: BrowserContext, tab_id: int) -> Page:
        """Get the Playwright Page for a tab, waking it from NVMe if necessary."""
        if tab_id not in self.tabs:
            raise ValueError(f"Tab {tab_id} does not exist.")
            
        vtab = self.tabs[tab_id]
        vtab.last_accessed = time.time()
        
        if vtab.status == "cold":
            print(f"[Hibernator] Waking tab {tab_id} from NVMe: {vtab.url}")
            await self._enforce_limits() # Make room if needed
            
            # Recreate page
            vtab.page = await context.new_page()
            
            # Load state from NVMe
            if vtab.hibernate_path.exists():
                state = json.loads(vtab.hibernate_path.read_text(encoding="utf-8"))
                await vtab.page.goto(state["url"], wait_until="domcontentloaded")
                
                # Restore web storage
                if "storage" in state and state["storage"]:
                    await vtab.page.evaluate("""(data) => {
                        try {
                            const ls = JSON.parse(data.localStorage || '{}');
                            for (const [k, v] of Object.entries(ls)) window.localStorage.setItem(k, v);
                            const ss = JSON.parse(data.sessionStorage || '{}');
                            for (const [k, v] of Object.entries(ss)) window.sessionStorage.setItem(k, v);
                        } catch(e) {}
                    }""", state["storage"])
                    
                await vtab.page.evaluate(f"window.scrollTo(0, {state['scroll_y']})")
                vtab.hibernate_path.unlink() # Delete hibernation file
            else:
                await vtab.page.goto(vtab.url, wait_until="domcontentloaded")
                
            vtab.status = "hot"
            
        return vtab.page

    async def _enforce_limits(self):
        """Find the oldest hot tabs and put them to sleep if we exceed max_hot_tabs."""
        hot_tabs = [t for t in self.tabs.values() if t.status == "hot"]
        if len(hot_tabs) >= self.max_hot_tabs:
            # Sort by oldest access time
            hot_tabs.sort(key=lambda t: t.last_accessed)
            
            # Hibernate the oldest until we are under the limit
            tabs_to_hibernate = len(hot_tabs) - self.max_hot_tabs + 1
            for i in range(tabs_to_hibernate):
                await self.hibernate_tab(hot_tabs[i])

    async def hibernate_tab(self, vtab: VirtualTab):
        """Serialize a tab's state to NVMe and kill its RAM process."""
        if vtab.status == "cold" or not vtab.page:
            return
            
        print(f"[Hibernator] Freezing tab {vtab.tab_id} to NVMe: {vtab.url}")
        
        try:
            # Extract state
            vtab.url = vtab.page.url
            scroll_y = await vtab.page.evaluate("window.scrollY")
            storage_data = await vtab.page.evaluate("""() => {
                return {
                    localStorage: JSON.stringify(window.localStorage),
                    sessionStorage: JSON.stringify(window.sessionStorage)
                };
            }""")
            
            # Save to NVMe
            state = {
                "url": vtab.url,
                "scroll_y": scroll_y,
                "storage": storage_data,
                "timestamp": time.time()
            }
            vtab.hibernate_path.write_text(json.dumps(state), encoding="utf-8")
            
            # Kill the chromium page process
            await vtab.page.close()
        except Exception as e:
            print(f"[Hibernator] Error freezing tab {vtab.tab_id}: {e}")
            
        vtab.page = None
        vtab.status = "cold"

    async def close_all(self):
        """Cleanup all tabs."""
        for vtab in self.tabs.values():
            if vtab.page and not vtab.page.is_closed():
                await vtab.page.close()
            if vtab.hibernate_path.exists():
                vtab.hibernate_path.unlink()
        self.tabs.clear()
