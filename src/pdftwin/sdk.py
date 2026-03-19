from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

from .agents.orchestrator import OrchestratorAgent
from .comparison.diff import compare_pdfs
from .config import config
from .models import Document
from .renderers.pdf_renderer import PdfRenderer
import fitz


@dataclass(frozen=True)
class RenderResult:
    output_pdf: Path


@dataclass(frozen=True)
class ReplicationResult:
    source_pdf: Path
    output_pdf: Path
    output_json: Path
    document: Document


@dataclass(frozen=True)
class DiffResult:
    original_pdf: Path
    recreated_pdf: Path
    pages: list[dict[str, Any]]
    summary: dict[str, Any]
    raw_result: dict[str, Any]


def extract_pdf(
    input_pdf: str | Path,
    *,
    model: Optional[str] = None,
    use_llm: Optional[bool] = None,
    debug: Optional[bool] = None,
) -> Document:
    input_path = _require_existing_file(input_pdf)

    with _temporary_config(model=model, use_llm=use_llm, debug=debug):
        doc = fitz.open(str(input_path))
        try:
            agent = OrchestratorAgent()
            result = agent.run(doc)
        finally:
            doc.close()

    return Document(pages=result["pages"], metadata=result["metadata"], traces=result["traces"])


def save_document(document: Document, output_json: str | Path) -> Path:
    output_path = Path(output_json).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document.model_dump_json(indent=2))
    return output_path


def load_document(input_json: str | Path) -> Document:
    input_path = _require_existing_file(input_json)
    return Document.model_validate_json(input_path.read_text())


def render_document(document: Document, output_pdf: str | Path) -> RenderResult:
    output_path = Path(output_pdf).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    PdfRenderer.render(document, str(output_path))
    return RenderResult(output_pdf=output_path)


def render_json(input_json: str | Path, output_pdf: str | Path) -> RenderResult:
    document = load_document(input_json)
    return render_document(document, output_pdf)


def replicate_pdf(
    input_pdf: str | Path,
    output_dir: str | Path | None = None,
    *,
    model: Optional[str] = None,
    use_llm: Optional[bool] = None,
    debug: Optional[bool] = None,
) -> ReplicationResult:
    input_path = _require_existing_file(input_pdf)
    resolved_output_dir = Path(output_dir).expanduser().resolve() if output_dir else Path.cwd()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    input_stem = f"{input_path.stem}_twin"
    output_pdf = resolved_output_dir / f"{input_stem}.pdf"
    output_json = resolved_output_dir / f"{input_stem}.json"

    document = extract_pdf(input_path, model=model, use_llm=use_llm, debug=debug)
    save_document(document, output_json)
    render_document(document, output_pdf)

    return ReplicationResult(
        source_pdf=input_path,
        output_pdf=output_pdf,
        output_json=output_json,
        document=document,
    )


def diff_pdfs(
    original_pdf: str | Path,
    recreated_pdf: str | Path,
    *,
    out_dir: str | Path | None = None,
    run_vl_on_all_pages: bool = False,
    dpi: int = 150,
) -> DiffResult:
    original_path = _require_existing_file(original_pdf)
    recreated_path = _require_existing_file(recreated_pdf)
    resolved_out_dir = str(Path(out_dir).expanduser().resolve()) if out_dir else None

    result = compare_pdfs(
        str(original_path),
        str(recreated_path),
        out_dir=resolved_out_dir,
        run_vl_on_all_pages=run_vl_on_all_pages,
        dpi=dpi,
    )
    return DiffResult(
        original_pdf=original_path,
        recreated_pdf=recreated_path,
        pages=result.get("pages", []),
        summary=result.get("summary", {}),
        raw_result=result,
    )


def _require_existing_file(path_like: str | Path) -> Path:
    path = Path(path_like).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    return path


@contextmanager
def _temporary_config(
    *,
    model: Optional[str] = None,
    use_llm: Optional[bool] = None,
    debug: Optional[bool] = None,
) -> Iterator[None]:
    original_values = {
        "model": config.model,
        "use_llm": config.use_llm,
        "debug": config.debug,
    }
    try:
        if model is not None:
            config.model = model
        if use_llm is not None:
            config.use_llm = use_llm
        if debug is not None:
            config.debug = debug
        yield
    finally:
        config.model = original_values["model"]
        config.use_llm = original_values["use_llm"]
        config.debug = original_values["debug"]
