import re
from typing import Tuple, Dict, List

class AutoEscalation:
    """
    Intelligent tier switching detection.
    """
    
    @staticmethod
    def detect_spa(html: str) -> bool:
        """Check for empty React/Vue/Angular/Next.js containers."""
        if not html:
            return False
        # Simplistic check for common empty root nodes
        spa_patterns = [
            r'<div\s+id="root">\s*</div>',
            r'<div\s+id="app">\s*</div>',
            r'<div\s+id="__next">\s*</div>',
            r'<app-root>\s*</app-root>'
        ]
        return any(re.search(pattern, html, re.IGNORECASE) for pattern in spa_patterns)

    @staticmethod
    def detect_cloudflare(html: str, headers: Dict[str, str]) -> bool:
        """Detect bot challenges."""
        server = headers.get("server", "").lower()
        if "cloudflare" in server and ("cf-browser-verification" in html or "Just a moment..." in html):
            return True
        return False

    @staticmethod
    def detect_visual_content(html: str) -> List[Dict[str, str]]:
        """Find charts/graphs/canvas elements, return placeholder info."""
        assets = []
        if "<canvas" in html or "<svg" in html or "chart" in html.lower():
            # Minimal placeholder since BeautifulSoup parsing will handle details in VisualSentinel
            assets.append({"type": "visual_element", "info": "Potential chart or canvas found."})
        return assets

    @staticmethod
    def detect_login_wall(html: str) -> bool:
        """Detect login forms blocking content."""
        if not html:
            return False
        login_patterns = [
            r'sign in', r'log in', r'password', r'forgot password'
        ]
        text_lower = html.lower()
        return all(pattern in text_lower for pattern in login_patterns)

    @classmethod
    def should_escalate(cls, html: str, headers: Dict[str, str]) -> Tuple[str, str]:
        """Returns (recommended_tier, reason)."""
        if cls.detect_cloudflare(html, headers):
            return "tier2", "Cloudflare bot challenge detected."
            
        if cls.detect_spa(html):
            return "tier2", "Empty SPA container detected (requires JS)."
            
        if cls.detect_login_wall(html):
            return "tier2", "Login wall detected."
            
        visuals = cls.detect_visual_content(html)
        if visuals:
            return "tier3", "Visual content (charts/canvas) detected requiring screenshots."
            
        return "tier1", "Text-based content."
