import pytest
import os
import io
import base64
from types import SimpleNamespace
import fitz
from PIL import Image
from src.pdftwin.models import (
    Document,
    Page,
    TextBlock,
    TextLine,
    TextSpan,
    BoundingBox,
    FontSpec,
    Provenance,
)
from src.pdftwin.config import config
from src.pdftwin.agents.orchestrator import OrchestratorAgent
from src.pdftwin.renderers.pdf_renderer import PdfRenderer
from src.pdftwin.cli import app
from src.pdftwin.llm.wrapper import LLMWrapper
from src.pdftwin.sdk import (
    diff_pdfs as sdk_diff_pdfs,
    extract_pdf as sdk_extract_pdf,
    load_document as sdk_load_document,
    render_json as sdk_render_json,
    replicate_pdf as sdk_replicate_pdf,
    save_document as sdk_save_document,
)
from typer.testing import CliRunner
from pydantic import BaseModel

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


def test_llm_wrapper_unwraps_schema_shaped_response(monkeypatch):
    class SampleModel(BaseModel):
        is_visually_identical: bool
        differences_found: list[str]

    monkeypatch.setattr(config, "use_llm", True)

    response_text = """```json
{"properties": {"is_visually_identical": true, "differences_found": []}, "type": "object"}
```"""

    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=response_text))]
    )
    monkeypatch.setattr("src.pdftwin.llm.wrapper.litellm.completion", lambda **kwargs: fake_response)

    result = LLMWrapper.call_structured(prompt="test", response_model=SampleModel)
    assert result.is_visually_identical is True
    assert result.differences_found == []


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


def test_extraction_uses_raster_fallback_for_garbled_sample_table(monkeypatch):
    monkeypatch.setattr(config, "use_llm", False)
    doc = fitz.open("tests/sample_pdfs/sample-table.pdf")
    agent = OrchestratorAgent()
    result = agent.run(doc)
    doc.close()

    first_page = result["pages"][0]
    assert len(first_page.images) == 1
    assert first_page.images[0].bbox.x0 == 0.0
    assert first_page.images[0].bbox.y0 == 0.0
    assert first_page.images[0].bbox.x1 == first_page.width
    assert first_page.images[0].bbox.y1 == first_page.height
    assert first_page.text_blocks


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


def test_sdk_extract_and_save_document(synthetic_pdf, tmp_path):
    document = sdk_extract_pdf(synthetic_pdf, use_llm=False)
    output_json = tmp_path / "sdk-document.json"

    saved_path = sdk_save_document(document, output_json)

    assert saved_path == output_json.resolve()
    assert output_json.exists()

    loaded_document = sdk_load_document(output_json)
    first_span_text = loaded_document.pages[0].text_blocks[0].lines[0].spans[0].text
    assert "Hello PDFTwin!" in first_span_text


def test_sdk_replicate_pdf_creates_pdf_and_json(synthetic_pdf, tmp_path):
    result = sdk_replicate_pdf(synthetic_pdf, tmp_path, use_llm=False)

    assert result.source_pdf.name == "test.pdf"
    assert result.output_pdf == (tmp_path / "test_twin.pdf").resolve()
    assert result.output_json == (tmp_path / "test_twin.json").resolve()
    assert result.output_pdf.exists()
    assert result.output_json.exists()
    assert result.document.pages


def test_sdk_render_json_and_diff(synthetic_pdf, tmp_path):
    replicated = sdk_replicate_pdf(synthetic_pdf, tmp_path, use_llm=False)
    rendered_pdf = tmp_path / "sdk-rendered.pdf"

    render_result = sdk_render_json(replicated.output_json, rendered_pdf)
    diff_result = sdk_diff_pdfs(synthetic_pdf, render_result.output_pdf, dpi=150)

    assert render_result.output_pdf == rendered_pdf.resolve()
    assert render_result.output_pdf.exists()
    assert diff_result.summary["evaluation_dpi"] == 150
    assert diff_result.pages
    assert diff_result.original_pdf.name == "test.pdf"


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


def test_render_full_page_image_shows_edited_text(tmp_path):
    image = Image.new("RGB", (220, 120), "white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    doc_ir = Document(
        pages=[
            Page(
                page_number=1,
                width=220,
                height=120,
                text_blocks=[
                    TextBlock(
                        lines=[
                            TextLine(
                                spans=[
                                    TextSpan(
                                        text="Hello HOMER",
                                        original_text="Hello",
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
                        "bbox": BoundingBox(x0=0, y0=0, x1=220, y1=120),
                        "width": 220,
                        "height": 120,
                        "image_base64": base64.b64encode(image_bytes.getvalue()).decode("utf-8"),
                        "provenance": Provenance(
                            agent_id="OrchestratorAgent", method="page_raster_fallback"
                        ),
                    }
                ],
                vectors=[],
                tables=[],
            )
        ]
    )

    output_pdf = str(tmp_path / "edited-visible.pdf")
    PdfRenderer.render(doc_ir, output_pdf)

    doc = fitz.open(output_pdf)
    page = doc[0]
    assert "Hello HOMER" in page.get_text()
    pix = page.get_pixmap(alpha=False)
    assert set(pix.samples) != {255}
    doc.close()


def test_render_full_page_image_shows_ocr_text_for_legacy_json(tmp_path):
    image = Image.new("RGB", (220, 120), "white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    doc_ir = Document(
        pages=[
            Page(
                page_number=1,
                width=220,
                height=120,
                text_blocks=[
                    TextBlock(
                        lines=[
                            TextLine(
                                spans=[
                                    TextSpan(
                                        text="Legacy HOMER text",
                                        bbox=BoundingBox(x0=20, y0=20, x1=120, y1=40),
                                        origin=(20, 40),
                                        font=FontSpec(name="Helvetica", size=18.0),
                                        provenance=Provenance(
                                            agent_id="OcrAgent", method="gemini-vision"
                                        ),
                                    )
                                ],
                                bbox=BoundingBox(x0=20, y0=20, x1=120, y1=40),
                            )
                        ],
                        bbox=BoundingBox(x0=20, y0=20, x1=120, y1=40),
                    )
                ],
                images=[
                    {
                        "bbox": BoundingBox(x0=0, y0=0, x1=220, y1=120),
                        "width": 220,
                        "height": 120,
                        "image_base64": base64.b64encode(image_bytes.getvalue()).decode("utf-8"),
                        "provenance": Provenance(
                            agent_id="OrchestratorAgent", method="page_raster_fallback"
                        ),
                    }
                ],
                vectors=[],
                tables=[],
            )
        ]
    )

    output_pdf = str(tmp_path / "legacy-visible.pdf")
    PdfRenderer.render(doc_ir, output_pdf)

    doc = fitz.open(output_pdf)
    page = doc[0]
    assert "Legacy HOMER text" in page.get_text()
    pix = page.get_pixmap(alpha=False)
    assert set(pix.samples) != {255}
    doc.close()


def test_cli_roundtrip(synthetic_pdf, tmp_path):
    output_dir = tmp_path / "artifacts"
    result = runner.invoke(app, [synthetic_pdf, "--output", str(output_dir)])
    assert result.exit_code == 0
    assert os.path.exists(output_dir / "test_twin.pdf")
    assert os.path.exists(output_dir / "test_twin.json")
    assert f"PDF output: {output_dir / 'test_twin.pdf'}" in result.stdout
    assert f"JSON output: {output_dir / 'test_twin.json'}" in result.stdout


def test_cli_roundtrip_default_output(synthetic_pdf, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, [synthetic_pdf])
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "test_twin.pdf")
    assert os.path.exists(tmp_path / "test_twin.json")
    assert f"PDF output: {tmp_path / 'test_twin.pdf'}" in result.stdout
    assert f"JSON output: {tmp_path / 'test_twin.json'}" in result.stdout


def test_cli_roundtrip_rejects_file_output_path(synthetic_pdf, tmp_path):
    result = runner.invoke(app, [synthetic_pdf, "--output", str(tmp_path / "out.pdf")])
    assert result.exit_code == 1

    captured_output = result.stdout
    if not captured_output:
        captured_output = getattr(result, "output", "")
    if not captured_output:
        try:
            captured_output = result.stderr
        except ValueError:
            captured_output = ""

    assert "expects a directory path" in captured_output


def test_cli_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "gemini" in result.stdout.lower()


def test_cli_inspect(synthetic_pdf):
    result = runner.invoke(app, ["inspect", synthetic_pdf])
    assert result.exit_code == 0
    assert "Pages: 1" in result.stdout
