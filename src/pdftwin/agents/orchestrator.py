import base64
from typing import Any, Dict

import fitz

from .base import BaseAgent
from .text_agent import TextAgent
from .image_agent import ImageAgent
from .vector_agent import VectorAgent
from .font_agent import FontAgent
from ..models import (
    Page,
    AgentTrace,
    Metadata,
    ImageObject,
    BoundingBox,
    TransformMatrix,
    Provenance,
    ConfidenceScore,
)


class OrchestratorAgent(BaseAgent):
    """Coordinates the document reconstruction process."""

    RASTER_FALLBACK_DPI = 300

    def __init__(self):
        self.text_agent = TextAgent()
        self.image_agent = ImageAgent()
        self.vector_agent = VectorAgent()
        self.font_agent = FontAgent()

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        doc: fitz.Document = context
        pages = []
        traces = []
        traces.append(
            self.record_trace("start", f"Orchestrating extraction for {doc.page_count} pages")
        )

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Run text extraction
            text_res = self.text_agent.run(page)
            text_blocks = text_res["text_blocks"]
            traces.extend(text_res["traces"])
            page_is_garbled = text_res.get("page_is_garbled", False)

            # Match fonts
            font_res = self.font_agent.run(text_blocks)
            text_blocks = font_res["text_blocks"]
            traces.extend(font_res["traces"])

            if page_is_garbled:
                images = [self._build_page_snapshot(page)]
                vectors = []
                traces.append(
                    self.record_trace(
                        "info",
                        f"Using page raster fallback for page {page_num + 1} due to garbled text extraction",
                    )
                )
            else:
                # Run image extraction
                img_res = self.image_agent.run(page, doc=doc)
                images = img_res["images"]
                traces.extend(img_res["traces"])

                # Run vector extraction
                vec_res = self.vector_agent.run(page)
                vectors = vec_res["vectors"]
                traces.extend(vec_res["traces"])

            pages.append(
                Page(
                    page_number=page_num + 1,
                    width=page.rect.width,
                    height=page.rect.height,
                    text_blocks=text_blocks,
                    images=images,
                    vectors=vectors,
                    tables=[],
                )
            )

        metadata = Metadata(
            title=doc.metadata.get("title"),
            author=doc.metadata.get("author"),
            creation_date=doc.metadata.get("creationDate"),
            producer=doc.metadata.get("producer"),
        )

        traces.append(self.record_trace("success", "Orchestration complete"))

        return {"pages": pages, "metadata": metadata, "traces": traces}

    def _build_page_snapshot(self, page: fitz.Page) -> ImageObject:
        pix = page.get_pixmap(dpi=self.RASTER_FALLBACK_DPI, alpha=False)
        rect = page.rect
        return ImageObject(
            bbox=BoundingBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1),
            width=pix.width,
            height=pix.height,
            image_base64=base64.b64encode(pix.tobytes("png")).decode("utf-8"),
            transform=TransformMatrix(),
            provenance=Provenance(agent_id=self.name, method="page_raster_fallback"),
            confidence=ConfidenceScore(score=1.0, agent_id=self.name),
        )
