from typing import Any, Dict
from .base import BaseAgent
from ..models import Page


class LayoutAgent(BaseAgent):
    """Reconstructs page geometry, reading order, etc."""

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        page_ir: Page = context
        traces = []
        traces.append(self.record_trace("start", "Layout processing started"))

        try:
            # Sort text blocks vertically then horizontally
            page_ir.text_blocks.sort(key=lambda b: (b.bbox.y0, b.bbox.x0))
            traces.append(self.record_trace("success", "Sorted blocks for reading order"))
        except Exception as e:
            traces.append(self.record_trace("error", str(e)))

        return {"page_ir": page_ir, "traces": traces}
