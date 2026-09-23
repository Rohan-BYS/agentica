import http.cookiejar
import json
import threading
from typing import List, Dict, Any

class SessionManager:
    """
    Manages cookies and state across all tiers.
    """
    def __init__(self):
        self.cookie_jar = http.cookiejar.CookieJar()
        self._lock = threading.Lock()

    def get_tier1_cookies(self) -> dict:
        """Get cookies for HTTP requests (Tier 1)."""
        with self._lock:
            return {c.name: c.value for c in self.cookie_jar}

    def get_cdp_cookies(self) -> List[Dict[str, Any]]:
        """Get cookies formatted for CDP Network.setCookies (Tier 2/3)."""
        cdp_cookies = []
        with self._lock:
            for c in self.cookie_jar:
                cookie_dict = {
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain,
                    "path": c.path,
                    "secure": c.secure,
                    "httpOnly": "HttpOnly" in (c._rest.keys() if hasattr(c, "_rest") else [])
                }
                # Handle Browser Use cookie normalization bug: strip expires=0
                if c.expires is not None and c.expires != 0:
                    cookie_dict["expires"] = c.expires
                cdp_cookies.append(cookie_dict)
        return cdp_cookies

    def export_storage_state(self, filepath: str) -> None:
        """Export Playwright-compatible storage_state.json."""
        state = {
            "cookies": self.get_cdp_cookies(),
            "origins": []
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f)

    def import_storage_state(self, filepath: str) -> None:
        """Import from Playwright-compatible storage_state.json."""
        with open(filepath, "r", encoding="utf-8") as f:
            state = json.load(f)
            
        with self._lock:
            for c in state.get("cookies", []):
                cookie = http.cookiejar.Cookie(
                    version=0, name=c["name"], value=c["value"], port=None, port_specified=False,
                    domain=c.get("domain", ""), domain_specified=bool(c.get("domain")),
                    domain_initial_dot=False, path=c.get("path", "/"), path_specified=bool(c.get("path")),
                    secure=c.get("secure", False), expires=c.get("expires"), discard=False,
                    comment=None, comment_url=None, rest={}
                )
                self.cookie_jar.set_cookie(cookie)

    def generate_local_storage_injection(self, origins_data: List[Dict[str, Any]]) -> str:
        """Generate JS to inject localStorage for given origins."""
        script = ""
        for origin in origins_data:
            script += f"if (window.location.origin === '{origin['origin']}') {{\n"
            for item in origin.get("localStorage", []):
                script += f"  localStorage.setItem('{item['name']}', '{item['value']}');\n"
            script += "}\n"
        return script
