from bs4 import BeautifulSoup
import re
from typing import List, Dict, Tuple
from src.core.visual_sentinel import VisualSentinel

class ContentExtractor:
    """
    HTML-to-Markdown compiler implementing Browser39 algorithms.
    """
    def __init__(self, visual_sentinel: VisualSentinel = None):
        self.links: List[str] = []
        self.visual_sentinel = visual_sentinel or VisualSentinel()

    def process_html(self, html: str, base_url: str = "") -> str:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Strip bidi overrides to prevent prompt injection
        for bdo in soup.find_all(['bdo', 'bdi']):
            bdo.unwrap()
            
        # Strip unwanted tags
        for tag in soup.find_all(['script', 'style', 'noscript', 'header', 'footer', 'nav']):
            tag.decompose()
            
        # Visual Sentinel Integration
        self.visual_sentinel.extract_visuals(soup)
        
        # Content preselection
        main_content = soup.find('main') or soup.find(role='main') or soup.find(id='content') or soup.find('article')
        if not main_content:
            main_content = soup.body if soup.body else soup
            
        return self._to_markdown(main_content, base_url)

    def _to_markdown(self, node, base_url: str) -> str:
        if not node:
            return ""
        if isinstance(node, str):
            return node.strip()

        markdown = ""
        for child in node.children:
            if isinstance(child, str):
                text = child.strip()
                if text:
                    markdown += text + " "
                continue

            tag_name = child.name
            if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(tag_name[1])
                markdown += f"\n\n{'#' * level} {self._to_markdown(child, base_url)}\n\n"
            elif tag_name == 'p':
                markdown += f"\n\n{self._to_markdown(child, base_url)}\n\n"
            elif tag_name == 'a':
                text = self._to_markdown(child, base_url)
                href = child.get('href', '')
                if text and href:
                    # Same-origin URL shortening
                    if href.startswith(base_url):
                        href = href[len(base_url):]
                        if not href.startswith('/'):
                            href = '/' + href
                    
                    if href not in self.links:
                        self.links.append(href)
                    idx = self.links.index(href)
                    markdown += f"[{text}][{idx}]"
                else:
                    markdown += text
            elif tag_name in ['b', 'strong']:
                text = self._to_markdown(child, base_url)
                if text:
                    markdown += f"**{text}**"
            elif tag_name in ['i', 'em']:
                text = self._to_markdown(child, base_url)
                if text:
                    markdown += f"*{text}*"
            elif tag_name == 'img':
                alt = child.get('alt', '')
                markdown += f"[Image: {alt}]" if alt else "[Image]"
            elif tag_name in ['ul', 'ol']:
                markdown += f"\n\n{self._to_markdown(child, base_url)}\n\n"
            elif tag_name == 'li':
                # Simplified list item handling
                markdown += f"\n* {self._to_markdown(child, base_url)}"
            elif tag_name == 'table':
                markdown += f"\n\n[Table Omitted]\n\n" # Simplified table for tier 1 text
            else:
                markdown += self._to_markdown(child, base_url)

        # Prune empty formatting
        markdown = re.sub(r'\*\*\s*\*\*', '', markdown)
        markdown = re.sub(r'\*\s*\*([^A-Za-z0-9]|$)', r'\1', markdown)
        
        # Cleanup extra newlines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        return markdown.strip()

    def get_links_markdown(self) -> str:
        """Returns the collected links for reference at the bottom of the page."""
        if not self.links:
            return ""
        refs = "\n\n--- Links ---\n"
        for i, link in enumerate(self.links):
            refs += f"[{i}]: {link}\n"
        return refs
