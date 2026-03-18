from typing import Any, Dict, List
import fitz  # PyMuPDF
from .base import BaseAgent
from ..models import VectorPath, DrawingStyle, BoundingBox, Provenance, ConfidenceScore


class VectorAgent(BaseAgent):
    """Extracts vector graphics and paths from a PDF page."""

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        page: fitz.Page = context
        vectors: List[VectorPath] = []
        traces = []
        traces.append(self.record_trace("start", "Vector extraction started"))

        try:
            drawings = page.get_drawings()
            for draw in drawings:
                style = DrawingStyle(
                    fill_color=tuple(draw.get("fill", (0, 0, 0)) or [])
                    if draw.get("fill")
                    else None,
                    stroke_color=tuple(draw.get("color", (0, 0, 0)) or [])
                    if draw.get("color")
                    else None,
                    stroke_width=draw.get("width", 1.0),
                    stroke_opacity=draw.get("stroke_opacity", 1.0),
                    fill_opacity=draw.get("fill_opacity", 1.0),
                    dashes=draw.get("dashes", None),
                )

                items = []
                for item in draw.get("items", []):
                    # PyMuPDF format is ("l", p1, p2) or ("c", p1, p2, p3, p4), etc.
                    # We store it similarly but sanitize tuples
                    op = item[0]
                    coords = [tuple(p) if hasattr(p, "__iter__") else p for p in item[1:]]
                    items.append((op, coords))

                rect = draw.get("rect")
                bbox = BoundingBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1) if rect else None

                vectors.append(
                    VectorPath(
                        items=items,
                        style=style,
                        bbox=bbox,
                        provenance=Provenance(agent_id=self.name, method="pymupdf_get_drawings"),
                        confidence=ConfidenceScore(score=0.9, agent_id=self.name),
                    )
                )

            traces.append(self.record_trace("success", f"Extracted {len(vectors)} vector paths"))
        except Exception as e:
            traces.append(self.record_trace("error", str(e)))

        return {"vectors": vectors, "traces": traces}
