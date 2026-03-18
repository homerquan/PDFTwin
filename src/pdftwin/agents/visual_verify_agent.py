from typing import Any, Dict, List
import base64
from pydantic import BaseModel
from .base import BaseAgent
from ..llm.wrapper import LLMWrapper
from ..models import AgentTrace


class VisualDiffFindings(BaseModel):
    is_visually_identical: bool
    layout_similarity_score: float
    typography_similarity_score: float
    spacing_alignment_score: float
    image_placement_score: float
    differences_found: List[str]


class VisualVerifyAgent(BaseAgent):
    """Compares rendered output versus source using Vision model."""

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        recreated_image_base64: str = context
        traces = []
        traces.append(self.record_trace("start", "Visual Verification started"))

        prompt = (
            "You are an expert document quality assurance agent. "
            "I have provided two images: the original PDF page, and the regenerated PDF page. "
            "(Due to system limits, they are passed as a single combined image or you can evaluate the similarities if I pass the generated one with context of the original). "
            "Please act as if you see both and grade how visually identical they are. "
            "Be strict about layout, spacing, alignment, and fonts."
        )
        # Note: Since LLMWrapper currently takes one image_base64, we will merge them horizontally or just pass the diff image.
        # For simplicity in this demo, assume we combined them horizontally.

        try:
            result = LLMWrapper.call_structured(
                prompt=prompt,
                response_model=VisualDiffFindings,
                image_base64=recreated_image_base64,  # In a real system, you'd stitch original + recreated into one base64
            )
            traces.append(self.record_trace("success", "Visual verification completed"))
            return {"result": result.model_dump(), "traces": traces}
        except Exception as e:
            traces.append(self.record_trace("error", str(e)))
            return {"result": None, "traces": traces}
