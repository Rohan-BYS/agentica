import asyncio
import httpx
import json
from bs4 import BeautifulSoup

from src.tiers.content_extractor import ContentExtractor
from src.core.secret_manager import SecretManager
from src.core.visual_sentinel import VisualSentinel
from src.core.auto_escalation import AutoEscalation

UNIFIED_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

class Tier1TextEngine:
    def __init__(self, secret_manager: SecretManager = None):
        self.client = httpx.AsyncClient(timeout=15.0, headers={"User-Agent": UNIFIED_USER_AGENT})
        self.secret_manager = secret_manager or SecretManager()
        self.visual_sentinel = VisualSentinel()

    def _get_headers(self) -> dict:
        return {
            "User-Agent": UNIFIED_USER_AGENT
        }

    async def fetch(self, url: str) -> str:
        """
        Tier 1: Fast HTTP fetching and text extraction.
        Zero rendering. Great for text-only research.
        """
        try:
            response = await self.client.get(url, follow_redirects=True, headers=self._get_headers())
            response.raise_for_status()
            
            # Charset auto-detection
            response.encoding = response.encoding or 'utf-8'
            content = response.text
            content_type = response.headers.get("Content-Type", "").lower()

            # RSS/Atom feed detection
            if "application/rss+xml" in content_type or "atom+xml" in content_type:
                return f"# RSS/Atom Feed\n\n{content}"

            # Content-type routing: JSON
            if "application/json" in content_type:
                try:
                    data = json.loads(content)
                    return f"# JSON Data\n\n```json\n{json.dumps(data, indent=2)}\n```"
                except:
                    pass

            # Extraction
            extractor = ContentExtractor(visual_sentinel=self.visual_sentinel)
            
            # Determine base_url
            parsed_url = httpx.URL(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.host}"
            
            markdown = extractor.process_html(content, base_url=base_url)
            markdown += extractor.get_links_markdown()

            # Secret Redaction
            markdown = self.secret_manager.redact(markdown)

            return f"# Extracted Content from {url}\n\n{markdown}"

        except Exception as e:
            return f"Error in Tier 1 fetch for {url}: {str(e)}"

    async def close(self):
        await self.client.aclose()
