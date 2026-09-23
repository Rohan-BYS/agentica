from bs4 import BeautifulSoup
from typing import List, Dict, Any

class VisualSentinel:
    """
    Detects visual elements during text extraction.
    """
    def __init__(self):
        self.asset_counter = 0
        self.visual_assets: Dict[int, Dict[str, Any]] = {}

    def extract_visuals(self, soup: BeautifulSoup) -> None:
        """
        Parse HTML for <canvas>, <svg>, <img>, <iframe> with chart-related attributes.
        Generate placeholder tokens and track assets.
        """
        visual_tags = soup.find_all(['canvas', 'svg', 'img', 'iframe'])
        
        for tag in visual_tags:
            is_chart_related = False
            class_str = " ".join(tag.get("class", [])).lower()
            id_str = tag.get("id", "").lower()
            
            if tag.name == 'canvas' or tag.name == 'svg':
                is_chart_related = True
            elif 'chart' in class_str or 'graph' in class_str or 'chart' in id_str or 'graph' in id_str:
                is_chart_related = True
                
            if is_chart_related:
                self.asset_counter += 1
                asset_id = self.asset_counter
                alt_text = tag.get("alt", tag.get("title", ""))
                
                asset_info = {
                    "id": asset_id,
                    "type": tag.name,
                    "alt": alt_text,
                    "selector": f"{tag.name}#{id_str}" if id_str else f"{tag.name}.{class_str.replace(' ', '.')}" if class_str else tag.name
                }
                
                self.visual_assets[asset_id] = asset_info
                
                # Create a placeholder element to replace the original tag
                placeholder_text = f'[VISUAL_ASSET: id={asset_id}, type="{tag.name}", alt="{alt_text}", selector="{asset_info["selector"]}"]'
                
                # Replace in soup
                if tag.string:
                    tag.string.replace_with(placeholder_text)
                else:
                    placeholder = soup.new_string(placeholder_text)
                    tag.replace_with(placeholder)

    def get_asset(self, asset_id: int) -> Dict[str, Any]:
        return self.visual_assets.get(asset_id, {})

    def scan_html(self, html: str) -> List[Dict[str, Any]]:
        """Parse HTML string for visual assets."""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        self.extract_visuals(soup)
        return list(self.visual_assets.values())

