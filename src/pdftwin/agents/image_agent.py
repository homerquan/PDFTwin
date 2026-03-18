from typing import Any, Dict, List
import base64
import fitz  # PyMuPDF
from .base import BaseAgent
from ..models import ImageObject, BoundingBox, TransformMatrix, Provenance, ConfidenceScore


class ImageAgent(BaseAgent):
    """Extracts images and their bounding boxes from a PDF page."""

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        page: fitz.Page = context
        doc: fitz.Document = kwargs.get("doc")
        images: List[ImageObject] = []
        traces = []
        traces.append(self.record_trace("start", "Image extraction started"))

        try:
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                base_img = doc.extract_image(xref)
                if not base_img:
                    continue

                img_bytes = base_img["image"]
                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                width = base_img["width"]
                height = base_img["height"]

                # Finding where the image is placed
                rects = page.get_image_rects(xref)
                for rect in rects:
                    images.append(
                        ImageObject(
                            bbox=BoundingBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1),
                            width=width,
                            height=height,
                            image_base64=img_base64,
                            transform=TransformMatrix(),  # Assume identity for simple rect mappings
                            provenance=Provenance(agent_id=self.name, method="pymupdf_get_images"),
                            confidence=ConfidenceScore(score=1.0, agent_id=self.name),
                        )
                    )

            traces.append(self.record_trace("success", f"Extracted {len(images)} images"))
        except Exception as e:
            traces.append(self.record_trace("error", str(e)))

        return {"images": images, "traces": traces}
