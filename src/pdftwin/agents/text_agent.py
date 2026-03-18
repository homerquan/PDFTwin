from typing import Any, Dict, List, Optional
import base64
import fitz  # PyMuPDF
from .base import BaseAgent
from ..config import config
from .ocr_agent import OcrAgent
from ..models import (
    TextBlock,
    TextLine,
    TextSpan,
    BoundingBox,
    FontSpec,
    ConfidenceScore,
    Provenance,
)


def _is_garbled(text: str) -> bool:
    if not text.strip():
        return False
    # count non-printable or control chars
    control_chars = sum(1 for c in text if ord(c) < 32 and c not in ["\n", "\r", "\t"])
    if control_chars / len(text) > 0.05:
        return True

    latin1_high = sum(1 for c in text if 128 <= ord(c) <= 255)
    letters = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    if latin1_high > 0 and latin1_high > letters * 2 and len(text) > 5:
        return True

    # Check for Private Use Area
    pua = sum(1 for c in text if 0xE000 <= ord(c) <= 0xF8FF)
    if pua / len(text) > 0.1:
        return True

    return False


class TextAgent(BaseAgent):
    """Extracts text, fonts, and bounding boxes using PyMuPDF."""

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        page: fitz.Page = context
        text_blocks: List[TextBlock] = []
        traces = []
        traces.append(self.record_trace("start", "Text extraction started"))

        try:
            page_dict = page.get_text("dict")
            ocr_calls = 0
            page_text_parts = []
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue

                b_bbox = block.get("bbox")
                lines: List[TextLine] = []

                block_text = ""

                for line in block.get("lines", []):
                    l_bbox = line.get("bbox")
                    dir_vec = line.get("dir", (1.0, 0.0))
                    spans: List[TextSpan] = []

                    for span in line.get("spans", []):
                        s_bbox = span.get("bbox")
                        color_int = span.get("color", 0)
                        r = ((color_int >> 16) & 255) / 255.0
                        g = ((color_int >> 8) & 255) / 255.0
                        b = (color_int & 255) / 255.0

                        font = FontSpec(
                            name=span.get("font", "Unknown"),
                            size=span.get("size", 10.0),
                            is_bold="Bold" in span.get("font", "")
                            or "bold" in span.get("font", ""),
                            is_italic="Italic" in span.get("font", "")
                            or "Oblique" in span.get("font", ""),
                            color=(r, g, b),
                        )

                        text = span.get("text", "")
                        block_text += text

                        text_span = TextSpan(
                            text=text,
                            bbox=BoundingBox(
                                x0=s_bbox[0], y0=s_bbox[1], x1=s_bbox[2], y1=s_bbox[3]
                            ),
                            origin=span.get("origin"),
                            font=font,
                            provenance=Provenance(
                                agent_id=self.name, method="pymupdf_get_text_dict"
                            ),
                            confidence=ConfidenceScore(score=1.0, agent_id=self.name),
                        )
                        spans.append(text_span)

                    lines.append(
                        TextLine(
                            spans=spans,
                            bbox=BoundingBox(
                                x0=l_bbox[0], y0=l_bbox[1], x1=l_bbox[2], y1=l_bbox[3]
                            ),
                            dir=dir_vec,
                        )
                    )

                # Check for garbled text
                if _is_garbled(block_text) and config.ocr_mode in ["auto", "llm"] and ocr_calls < 5:
                    ocr_calls += 1
                    traces.append(
                        self.record_trace(
                            "info",
                            f"Garbled text detected. Falling back to OCR for block at {b_bbox}",
                        )
                    )

                    # render this specific rect
                    rect = fitz.Rect(b_bbox)
                    pix = page.get_pixmap(clip=rect, dpi=150)
                    img_base64 = base64.b64encode(pix.tobytes("jpeg")).decode("utf-8")

                    ocr_agent = OcrAgent()
                    res = ocr_agent.run(img_base64)
                    traces.extend(res["traces"])

                    ocr_result = res.get("result")
                    if ocr_result and ocr_result.has_text:
                        # Override the whole block with the OCR'd text using the first span's style as fallback
                        if lines and lines[0].spans:
                            fallback_font = lines[0].spans[0].font
                            fallback_origin = lines[0].spans[0].origin
                        else:
                            fallback_font = FontSpec(name="Helvetica", size=10.0)
                            fallback_origin = (b_bbox[0], b_bbox[3])

                        # Wipe the old lines and create a single new one
                        lines = [
                            TextLine(
                                spans=[
                                    TextSpan(
                                        text=ocr_result.text,
                                        bbox=BoundingBox(
                                            x0=b_bbox[0], y0=b_bbox[1], x1=b_bbox[2], y1=b_bbox[3]
                                        ),
                                        origin=fallback_origin,
                                        font=fallback_font,
                                        provenance=Provenance(
                                            agent_id="OcrAgent", method="gemini-vision"
                                        ),
                                        confidence=ConfidenceScore(
                                            score=ocr_result.confidence, agent_id="OcrAgent"
                                        ),
                                    )
                                ],
                                bbox=BoundingBox(
                                    x0=b_bbox[0], y0=b_bbox[1], x1=b_bbox[2], y1=b_bbox[3]
                                ),
                                dir=(1.0, 0.0),
                            )
                        ]

                page_text_parts.append(block_text)
                text_blocks.append(
                    TextBlock(
                        lines=lines,
                        bbox=BoundingBox(x0=b_bbox[0], y0=b_bbox[1], x1=b_bbox[2], y1=b_bbox[3]),
                        block_type=0,
                        provenance=Provenance(agent_id=self.name, method="pymupdf_get_text_dict"),
                        confidence=ConfidenceScore(score=1.0, agent_id=self.name),
                    )
                )
            traces.append(self.record_trace("success", f"Extracted {len(text_blocks)} text blocks"))
        except Exception as e:
            traces.append(self.record_trace("error", str(e)))

        page_text = " ".join(part for part in page_text_parts if part.strip())
        page_is_garbled = _is_garbled(page_text) if page_text else False

        return {
            "text_blocks": text_blocks,
            "traces": traces,
            "page_is_garbled": page_is_garbled,
        }
