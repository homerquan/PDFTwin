import base64
import os
import fitz
import numpy as np
from PIL import Image, ImageChops, ImageStat
from typing import Dict, Any, Tuple, Optional
from ..agents.visual_verify_agent import VisualVerifyAgent


def page_to_image(page: fitz.Page, dpi: int = 150) -> Image.Image:
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def create_diff_image(img1: Image.Image, img2: Image.Image) -> Tuple[Image.Image, float]:
    """Creates a visual diff image and returns the pixel difference percentage."""
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    diff = ImageChops.difference(img1, img2)

    # Calculate difference percentage based on mean pixel value
    stat = ImageStat.Stat(diff)
    diff_percent = sum(stat.mean) / (255.0 * 3) * 100

    # Highlight differences
    diff_highlight = diff.point(lambda p: p * 255)  # Make differences stark white
    return diff_highlight, diff_percent


def compare_pdfs(
    original_pdf: str, recreated_pdf: str, out_dir: Optional[str] = None
) -> Dict[str, Any]:
    doc1 = fitz.open(original_pdf)
    doc2 = fitz.open(recreated_pdf)

    if len(doc1) != len(doc2):
        return {
            "error": "Page counts differ",
            "original_pages": len(doc1),
            "recreated_pages": len(doc2),
        }

    page_reports = []
    agent = VisualVerifyAgent()

    for i in range(len(doc1)):
        img1 = page_to_image(doc1[i])
        img2 = page_to_image(doc2[i])

        diff_img, diff_percent = create_diff_image(img1, img2)

        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            diff_img.save(os.path.join(out_dir, f"page_{i + 1}_diff.png"))
            img1.save(os.path.join(out_dir, f"page_{i + 1}_orig.png"))
            img2.save(os.path.join(out_dir, f"page_{i + 1}_regen.png"))

        # Optional: Ask the LLM agent using a combined image
        combined = Image.new("RGB", (img1.width + img2.width, img1.height))
        combined.paste(img1, (0, 0))
        combined.paste(img2, (img1.width, 0))

        # Save to buffer for base64
        import io

        buffer = io.BytesIO()
        combined.save(buffer, format="JPEG")
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        if i == 0:  # Only run VL check on first page to speed up evaluation
            try:
                vl_res = agent.run(context=b64)
                vl_findings = vl_res.get("result", {})
            except Exception as e:
                vl_findings = {"error": str(e)}
        else:
            vl_findings = {"skipped": "VL check skipped for pages > 1"}

        page_reports.append(
            {
                "page": i + 1,
                "deterministic_diff_percentage": diff_percent,
                "vl_findings": vl_findings,
            }
        )

    return {"pages": page_reports}
