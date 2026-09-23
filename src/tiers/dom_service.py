"""
DOM Service: Parallel CDP DOM extraction engine.
Extracts DOM snapshot, accessibility tree, and bounding boxes concurrently.

Inspired by Browser Use's dom/service.py and dom/enhanced_snapshot.py.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Tuple


@dataclass
class DOMRect:
    """Represents a bounding rectangle in CSS pixels."""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def area(self) -> float:
        return self.width * self.height

    def contains(self, other: "DOMRect", threshold: float = 0.99) -> bool:
        """Check if this rect contains another rect by area overlap."""
        if self.area == 0:
            return False
        # Calculate intersection
        ix1 = max(self.x, other.x)
        iy1 = max(self.y, other.y)
        ix2 = min(self.x + self.width, other.x + other.width)
        iy2 = min(self.y + self.height, other.y + other.height)
        if ix2 <= ix1 or iy2 <= iy1:
            return False
        intersection_area = (ix2 - ix1) * (iy2 - iy1)
        return (intersection_area / max(other.area, 1e-9)) >= threshold


@dataclass
class EnhancedDOMNode:
    """A DOM node enriched with accessibility info and bounding box."""
    node_id: int = 0
    backend_node_id: int = 0
    tag_name: str = ""
    role: str = ""
    name: str = ""
    value: str = ""
    is_interactive: bool = False
    is_visible: bool = True
    bounds: DOMRect = field(default_factory=DOMRect)
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List["EnhancedDOMNode"] = field(default_factory=list)
    selector_index: Optional[int] = None


# 10 critical computed styles (from Browser Use)
CRITICAL_STYLES = [
    "display", "visibility", "opacity", "overflow",
    "overflow-x", "overflow-y", "cursor", "pointer-events",
    "position", "background-color",
]


class DOMService:
    """
    Parallel CDP DOM extraction engine.
    Executes 3 concurrent CDP queries and reconciles into unified tree.
    """

    def __init__(self, cdp_session):
        self.cdp = cdp_session
        self._clickable_set: Set[int] = set()

    async def extract_full_state(self, device_pixel_ratio: float = 1.0) -> Dict:
        """
        Run 3 parallel CDP extractions and return unified DOM state.

        Returns dict with:
        - dom_tree: full DOM tree with nodes
        - ax_tree: accessibility tree
        - clickable_node_ids: set of clickable backend node IDs
        - bounding_boxes: dict of backend_node_id -> DOMRect
        """
        # Run all 3 CDP queries concurrently (with timeout)
        try:
            snapshot_task = self.cdp.send("DOMSnapshot.captureSnapshot", {
                "computedStyles": CRITICAL_STYLES,
                "includeDOMRects": True,
                "includePaintOrder": True,
            })
            dom_task = self.cdp.send("DOM.getDocument", {
                "depth": -1,
                "pierce": True,
            })
            ax_task = self.cdp.send("Accessibility.getFullAXTree")

            results = await asyncio.wait_for(
                asyncio.gather(snapshot_task, dom_task, ax_task, return_exceptions=True),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            return {"error": "CDP extraction timed out after 10s"}

        snapshot_result, dom_result, ax_result = results

        state = {
            "dom_tree": dom_result if not isinstance(dom_result, Exception) else None,
            "ax_tree": ax_result if not isinstance(ax_result, Exception) else None,
            "snapshot": snapshot_result if not isinstance(snapshot_result, Exception) else None,
            "clickable_node_ids": set(),
            "bounding_boxes": {},
        }

        # Process snapshot for bounding boxes and clickable elements
        if state["snapshot"] and not isinstance(state["snapshot"], Exception):
            self._process_snapshot(state, device_pixel_ratio)

        return state

    def _process_snapshot(self, state: Dict, dpr: float):
        """Process DOMSnapshot result to extract bounding boxes and clickable info."""
        snapshot = state["snapshot"]
        documents = snapshot.get("documents", [])
        if not documents:
            return

        doc = documents[0]
        layout = doc.get("layout", {})
        nodes = doc.get("nodes", {})

        # O(1) clickable set optimization (3000x speedup from Browser Use)
        is_clickable = nodes.get("isClickable", {})
        clickable_indices = is_clickable.get("index", [])
        state["clickable_node_ids"] = set(clickable_indices)  # list -> set = O(1) lookup
        self._clickable_set = state["clickable_node_ids"]

        # Extract bounding boxes
        node_indices = layout.get("nodeIndex", [])
        bounds_list = layout.get("bounds", [])

        backend_node_ids = nodes.get("backendNodeId", [])

        for i, node_idx in enumerate(node_indices):
            if i < len(bounds_list) and node_idx < len(backend_node_ids):
                raw_bounds = bounds_list[i]
                if len(raw_bounds) >= 4:
                    bid = backend_node_ids[node_idx]
                    # Normalize from device pixels to CSS pixels
                    state["bounding_boxes"][bid] = DOMRect(
                        x=raw_bounds[0] / dpr,
                        y=raw_bounds[1] / dpr,
                        width=raw_bounds[2] / dpr,
                        height=raw_bounds[3] / dpr,
                    )

    def should_collapse_child(self, parent_bounds: DOMRect, child_bounds: DOMRect,
                               threshold: float = 0.99) -> bool:
        """
        Check if child should be collapsed into parent (99% containment rule).
        From Browser Use's serializer.
        """
        return parent_bounds.contains(child_bounds, threshold)

    async def get_viewport_size(self) -> Tuple[int, int]:
        """Get current viewport dimensions."""
        try:
            result = await self.cdp.send("Runtime.evaluate", {
                "expression": "JSON.stringify({w: window.innerWidth, h: window.innerHeight})",
                "returnByValue": True,
            })
            import json
            data = json.loads(result["result"]["value"])
            return (data["w"], data["h"])
        except Exception:
            return (1280, 800)
