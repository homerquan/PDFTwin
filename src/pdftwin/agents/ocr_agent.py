from typing import Any, Dict, List
import base64
from pydantic import BaseModel
import fitz
from .base import BaseAgent
from ..llm.wrapper import LLMWrapper
from ..models import AgentTrace


class OcrResult(BaseModel):
    has_text: bool
    text: str
    confidence: float


class OcrAgent(BaseAgent):
    """Uses LLM (Gemini) for OCR fallback on images."""

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        image_base64: str = context
        traces = []
        traces.append(self.record_trace("start", "OCR extraction started"))

        prompt = "Extract any readable text from this image perfectly. Preserve line breaks. If there is no text, return has_text=false."

        try:
            result = LLMWrapper.call_structured(
                prompt=prompt, response_model=OcrResult, image_base64=image_base64
            )
            traces.append(self.record_trace("success", "OCR completed successfully"))
            return {"result": result, "traces": traces}
        except Exception as e:
            traces.append(self.record_trace("error", str(e)))
            return {"result": None, "traces": traces}
