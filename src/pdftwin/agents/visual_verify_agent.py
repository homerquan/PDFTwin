from typing import Any, Dict, List
from pydantic import BaseModel
from .base import BaseAgent
from ..llm.wrapper import LLMWrapper
from ..models import AgentTrace


class VisualDiffFindings(BaseModel):
    is_visually_identical: bool
    overall_similarity_score: float
    layout_similarity_score: float
    typography_similarity_score: float
    spacing_alignment_score: float
    image_placement_score: float
    table_structure_score: float
    text_corruption_detected: bool
    text_overflow_detected: bool
    table_issues: List[str]
    text_issues: List[str]
    image_issues: List[str]
    differences_found: List[str]


class VisualVerifyAgent(BaseAgent):
    """Compares rendered output versus source using Vision model."""

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        recreated_image_base64: str = context
        traces = []
        traces.append(self.record_trace("start", "Visual Verification started"))

        prompt = (
            "You are an expert document quality assurance agent. "
            "You are given one combined image with the original PDF page on the LEFT and the regenerated PDF page on the RIGHT. "
            "Evaluate whether the regenerated page is visually identical to the original. "
            "Be extremely strict about text correctness, corrupted characters, missing or extra text, line wrapping, table alignment, table borders, row and column structure, image placement, spacing, and typography. "
            "If there are no visible problems, return empty issue lists. "
            "If the page contains a table, pay special attention to cell alignment, overlaps, and broken line wraps."
        )

        try:
            result = LLMWrapper.call_structured(
                prompt=prompt,
                response_model=VisualDiffFindings,
                image_base64=recreated_image_base64,
            )
            traces.append(self.record_trace("success", "Visual verification completed"))
            return {"result": result.model_dump(), "traces": traces}
        except Exception as e:
            traces.append(self.record_trace("error", str(e)))
            return {"result": None, "traces": traces}
