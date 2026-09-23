"""
Selector Path Generator: Minimal, stable CSS selector generation.
Port of Lightpanda's SelectorPath.zig algorithm.

Generates the shortest possible CSS selector that uniquely identifies
a DOM element, using a multi-step strategy:
1. Try unique #id
2. Qualify with stable attributes (name, data-testid, etc.)
3. Use :has() descendant disambiguation
4. Fall back to :nth-of-type(n)
5. Greedy ancestor climbing
"""

from __future__ import annotations
from typing import Optional


# Stable attributes to check (in priority order)
STABLE_ATTRIBUTES = [
    "data-testid", "data-test-id", "data-cy",
    "name", "aria-label", "title", "placeholder",
    "type", "role",
]


class SelectorPathGenerator:
    """
    Generates minimal, stable CSS selectors for DOM elements.
    Designed to produce selectors that survive DOM mutations and
    dynamic content changes.
    """

    def __init__(self, page):
        """
        Args:
            page: Playwright Page object for evaluating selectors.
        """
        self.page = page

    async def build(self, backend_node_id: int) -> Optional[str]:
        """
        Generate the minimal unique CSS selector for a DOM element.

        Args:
            backend_node_id: The CDP backend node ID of the target element.

        Returns:
            A CSS selector string, or None if generation fails.
        """
        js = f"""() => {{
            // Resolve the element from backend node ID (we'll use a data attr for lookup)
            const all = document.querySelectorAll('*');
            let target = null;

            // Try to find element by iterating (since we can't directly access by backendNodeId from JS)
            // This is a fallback; normally the element would be identified by the CDP session
            for (const el of all) {{
                if (el.getAttribute('data-nexus-bid') === '{backend_node_id}') {{
                    target = el;
                    break;
                }}
            }}

            if (!target) return null;

            function isUniqueSelector(selector) {{
                try {{
                    const matches = document.querySelectorAll(selector);
                    return matches.length === 1 && matches[0] === target;
                }} catch(e) {{ return false; }}
            }}

            function matchCount(selector) {{
                try {{ return document.querySelectorAll(selector).length; }}
                catch(e) {{ return 999; }}
            }}

            // Step 1: Try #id
            if (target.id && /^[a-zA-Z][\\w-]*$/.test(target.id)) {{
                const sel = '#' + CSS.escape(target.id);
                if (isUniqueSelector(sel)) return sel;
            }}

            const tag = target.tagName.toLowerCase();

            // Step 2: Try tag + stable attributes
            const stableAttrs = {STABLE_ATTRIBUTES};
            for (const attr of stableAttrs) {{
                const val = target.getAttribute(attr);
                if (val) {{
                    const sel = tag + '[' + attr + '=' + JSON.stringify(val) + ']';
                    if (isUniqueSelector(sel)) return sel;
                }}
            }}

            // Step 3: Try :has() with unique descendant
            const children = target.querySelectorAll('*');
            for (const child of children) {{
                if (child.id) {{
                    const sel = tag + ':has(#' + CSS.escape(child.id) + ')';
                    if (isUniqueSelector(sel)) return sel;
                }}
                for (const attr of stableAttrs) {{
                    const val = child.getAttribute(attr);
                    if (val) {{
                        const childTag = child.tagName.toLowerCase();
                        const sel = tag + ':has(' + childTag + '[' + attr + '=' + JSON.stringify(val) + '])';
                        if (isUniqueSelector(sel)) return sel;
                    }}
                }}
            }}

            // Step 4: Try :nth-of-type
            let nthIndex = 1;
            let sibling = target.previousElementSibling;
            while (sibling) {{
                if (sibling.tagName === target.tagName) nthIndex++;
                sibling = sibling.previousElementSibling;
            }}
            const nthSel = tag + ':nth-of-type(' + nthIndex + ')';

            // Step 5: Greedy ancestor climbing
            let candidate = nthSel;
            let count = matchCount(candidate);

            if (count === 1) return candidate;

            let ancestor = target.parentElement;
            let depth = 0;
            while (ancestor && ancestor !== document.body && depth < 5) {{
                let ancestorSel = ancestor.tagName.toLowerCase();
                if (ancestor.id) {{
                    ancestorSel = '#' + CSS.escape(ancestor.id);
                }} else {{
                    for (const attr of stableAttrs) {{
                        const val = ancestor.getAttribute(attr);
                        if (val) {{
                            ancestorSel += '[' + attr + '=' + JSON.stringify(val) + ']';
                            break;
                        }}
                    }}
                }}

                const trial = ancestorSel + ' ' + candidate;
                const trialCount = matchCount(trial);
                if (trialCount > 0 && trialCount < count) {{
                    candidate = trial;
                    count = trialCount;
                    if (count === 1) return candidate;
                }}

                ancestor = ancestor.parentElement;
                depth++;
            }}

            return candidate;
        }}"""

        try:
            result = await self.page.evaluate(js)
            return result
        except Exception:
            return None

    async def build_from_element(self, element_handle) -> Optional[str]:
        """
        Generate a selector for a Playwright ElementHandle.

        Args:
            element_handle: A Playwright ElementHandle.

        Returns:
            CSS selector string or None.
        """
        js = """(el) => {
            function isUniqueSelector(selector, target) {
                try {
                    const matches = document.querySelectorAll(selector);
                    return matches.length === 1 && matches[0] === target;
                } catch(e) { return false; }
            }

            // Try #id
            if (el.id && /^[a-zA-Z][\\w-]*$/.test(el.id)) {
                const sel = '#' + CSS.escape(el.id);
                if (isUniqueSelector(sel, el)) return sel;
            }

            const tag = el.tagName.toLowerCase();
            const stableAttrs = ['data-testid', 'name', 'aria-label', 'title', 'placeholder', 'type'];

            for (const attr of stableAttrs) {
                const val = el.getAttribute(attr);
                if (val) {
                    const sel = tag + '[' + attr + '=' + JSON.stringify(val) + ']';
                    if (isUniqueSelector(sel, el)) return sel;
                }
            }

            // nth-of-type with parent context
            let nthIndex = 1;
            let sibling = el.previousElementSibling;
            while (sibling) {
                if (sibling.tagName === el.tagName) nthIndex++;
                sibling = sibling.previousElementSibling;
            }

            let candidate = tag + ':nth-of-type(' + nthIndex + ')';
            let ancestor = el.parentElement;
            if (ancestor && ancestor.id) {
                candidate = '#' + CSS.escape(ancestor.id) + ' > ' + candidate;
            } else if (ancestor) {
                candidate = ancestor.tagName.toLowerCase() + ' > ' + candidate;
            }

            return candidate;
        }"""
        try:
            result = await element_handle.evaluate(js)
            return result
        except Exception:
            return None
