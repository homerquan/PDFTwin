import base64
import fitz
from ..models import Document, Page


class PdfRenderer:
    """Regenerates a visually matching PDF from the Intermediate Representation."""

    FULL_PAGE_IMAGE_COVERAGE = 0.95

    @classmethod
    def render(cls, ir_doc: Document, output_path: str):
        doc = fitz.open()

        for page_ir in ir_doc.pages:
            page = doc.new_page(width=page_ir.width, height=page_ir.height)
            cls._render_page(page, page_ir)

        if ir_doc.metadata.title:
            doc.set_metadata(
                {
                    "title": ir_doc.metadata.title,
                    "author": ir_doc.metadata.author,
                    "producer": "PDFTwin",
                }
            )

        doc.save(output_path)
        doc.close()

    @classmethod
    def _render_page(cls, page: fitz.Page, page_ir: Page):
        render_text_invisibly = cls._should_render_text_invisibly(page_ir)

        # 1. Render Vectors (drawings)
        for vector in page_ir.vectors:
            shape = page.new_shape()
            for op, coords in vector.items:
                if op == "l":  # line
                    shape.draw_line(fitz.Point(coords[0]), fitz.Point(coords[1]))
                elif op == "c":  # curve
                    shape.draw_bezier(
                        fitz.Point(coords[0]),
                        fitz.Point(coords[1]),
                        fitz.Point(coords[2]),
                        fitz.Point(coords[3]),
                    )
                elif op == "re":  # rect
                    shape.draw_rect(fitz.Rect(coords[0]))
                elif op == "qu":  # quad
                    shape.draw_quad(fitz.Quad(coords[0]))

            if vector.style.fill_color:
                shape.finish(
                    fill=vector.style.fill_color,
                    color=vector.style.stroke_color,
                    width=vector.style.stroke_width or 1.0,
                    stroke_opacity=vector.style.stroke_opacity,
                    fill_opacity=vector.style.fill_opacity,
                    dashes=vector.style.dashes,
                )
            else:
                shape.finish(
                    color=vector.style.stroke_color,
                    width=vector.style.stroke_width or 1.0,
                    stroke_opacity=vector.style.stroke_opacity,
                    fill_opacity=vector.style.fill_opacity,
                    dashes=vector.style.dashes,
                )
            shape.commit()

        # 2. Render Images
        for image_ir in page_ir.images:
            img_bytes = base64.b64decode(image_ir.image_base64)
            rect = fitz.Rect(image_ir.bbox.x0, image_ir.bbox.y0, image_ir.bbox.x1, image_ir.bbox.y1)
            page.insert_image(rect, stream=img_bytes)

        # 3. Render Text
        for block in page_ir.text_blocks:
            for line in block.lines:
                for span in line.spans:
                    fontname = span.font.matched_font or "Helvetica"

                    try:
                        # try inserting text with specified font properties
                        if span.origin:
                            point = fitz.Point(span.origin[0], span.origin[1])
                        else:
                            point = fitz.Point(span.bbox.x0, span.bbox.y1)  # fallback

                        page.insert_text(
                            point,
                            span.text,
                            fontname=fontname,
                            fontsize=span.font.size,
                            color=span.font.color,
                            render_mode=3 if render_text_invisibly else 0,
                        )
                    except Exception as e:
                        print(f"Failed to render text span '{span.text}': {e}")

    @classmethod
    def _should_render_text_invisibly(cls, page_ir: Page) -> bool:
        return cls._has_full_page_image(page_ir) and cls._has_text(page_ir)

    @classmethod
    def _has_full_page_image(cls, page_ir: Page) -> bool:
        page_area = page_ir.width * page_ir.height
        if page_area <= 0:
            return False

        for image_ir in page_ir.images:
            width = max(image_ir.bbox.x1 - image_ir.bbox.x0, 0)
            height = max(image_ir.bbox.y1 - image_ir.bbox.y0, 0)
            if (width * height) / page_area >= cls.FULL_PAGE_IMAGE_COVERAGE:
                return True

        return False

    @staticmethod
    def _has_text(page_ir: Page) -> bool:
        return any(
            span.text.strip()
            for block in page_ir.text_blocks
            for line in block.lines
            for span in line.spans
        )
