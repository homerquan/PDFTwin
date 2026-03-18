import pytest
import os
import io
import base64
import fitz
from PIL import Image
from src.pdftwin.models import Document, Page, TextBlock, TextLine, TextSpan, BoundingBox, FontSpec
from src.pdftwin.config import config
from src.pdftwin.agents.orchestrator import OrchestratorAgent
from src.pdftwin.renderers.pdf_renderer import PdfRenderer
from src.pdftwin.cli import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def synthetic_pdf(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    # Draw some text
    page.insert_text(fitz.Point(50, 50), "Hello PDFTwin!", fontsize=12, fontname="Helvetica")
    # Draw a line (vector)
    page.draw_line(fitz.Point(50, 70), fitz.Point(200, 70))
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


def test_models_serialization():
    span = TextSpan(
        text="Hello",
        bbox=BoundingBox(x0=0, y0=0, x1=10, y1=10),
        font=FontSpec(name="Arial", size=10.0),
    )
    data = span.model_dump_json()
    assert "Hello" in data

    span2 = TextSpan.model_validate_json(data)
    assert span2.text == "Hello"


def test_extraction_orchestrator(synthetic_pdf):
    doc = fitz.open(synthetic_pdf)
    agent = OrchestratorAgent()
    result = agent.run(doc)

    assert "pages" in result
    assert len(result["pages"]) == 1
    page_ir = result["pages"][0]

    assert page_ir.width == 595.0
    assert page_ir.height == 842.0
    assert len(page_ir.text_blocks) > 0

    text = "".join([span.text for line in page_ir.text_blocks[0].lines for span in line.spans])
    assert "Hello PDFTwin!" in text


def test_render_roundtrip(synthetic_pdf, tmp_path):
    doc = fitz.open(synthetic_pdf)
    agent = OrchestratorAgent()
    result = agent.run(doc)
    doc.close()

    doc_ir = Document(pages=result["pages"], metadata=result["metadata"], traces=result["traces"])
    output_pdf = str(tmp_path / "output.pdf")

    PdfRenderer.render(doc_ir, output_pdf)
    assert os.path.exists(output_pdf)

    # Verify the output PDF
    doc2 = fitz.open(output_pdf)
    page2 = doc2[0]
    text2 = page2.get_text()
    assert "Hello PDFTwin!" in text2
    doc2.close()


def test_render_full_page_image_keeps_text_searchable_but_invisible(tmp_path):
    image = Image.new("RGB", (200, 100), "white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    doc_ir = Document(
        pages=[
            Page(
                page_number=1,
                width=200,
                height=100,
                text_blocks=[
                    TextBlock(
                        lines=[
                            TextLine(
                                spans=[
                                    TextSpan(
                                        text="Hello",
                                        bbox=BoundingBox(x0=20, y0=20, x1=70, y1=40),
                                        origin=(20, 40),
                                        font=FontSpec(name="Helvetica", size=18.0),
                                    )
                                ],
                                bbox=BoundingBox(x0=20, y0=20, x1=70, y1=40),
                            )
                        ],
                        bbox=BoundingBox(x0=20, y0=20, x1=70, y1=40),
                    )
                ],
                images=[
                    {
                        "bbox": BoundingBox(x0=0, y0=0, x1=200, y1=100),
                        "width": 200,
                        "height": 100,
                        "image_base64": base64.b64encode(image_bytes.getvalue()).decode("utf-8"),
                    }
                ],
                vectors=[],
                tables=[],
            )
        ]
    )

    output_pdf = str(tmp_path / "full-page-image.pdf")
    PdfRenderer.render(doc_ir, output_pdf)

    doc = fitz.open(output_pdf)
    page = doc[0]

    assert "Hello" in page.get_text()

    pix = page.get_pixmap(alpha=False)
    assert set(pix.samples) == {255}
    doc.close()


def test_cli_roundtrip(synthetic_pdf, tmp_path):
    out_pdf = str(tmp_path / "out.pdf")
    result = runner.invoke(app, [synthetic_pdf, "--output", out_pdf])
    assert result.exit_code == 0
    assert os.path.exists(out_pdf)
    assert os.path.exists(tmp_path / "out.json")
    assert f"PDF output: {out_pdf}" in result.stdout
    assert f"JSON output: {tmp_path / 'out.json'}" in result.stdout


def test_cli_roundtrip_default_output(synthetic_pdf, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, [synthetic_pdf])
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "test_twin.pdf")
    assert os.path.exists(tmp_path / "test_twin.json")
    assert f"PDF output: {tmp_path / 'test_twin.pdf'}" in result.stdout
    assert f"JSON output: {tmp_path / 'test_twin.json'}" in result.stdout


def test_cli_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "gemini" in result.stdout.lower()


def test_cli_inspect(synthetic_pdf):
    result = runner.invoke(app, ["inspect", synthetic_pdf])
    assert result.exit_code == 0
    assert "Pages: 1" in result.stdout
