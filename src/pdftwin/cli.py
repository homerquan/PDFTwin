import json
import os
import sys
from pathlib import Path
from typing import Optional

import fitz
import typer

from .models import Document
from .agents.orchestrator import OrchestratorAgent
from .renderers.pdf_renderer import PdfRenderer
from .comparison.diff import compare_pdfs
from .config import config


class DefaultToRoundtripGroup(typer.core.TyperGroup):
    def resolve_command(self, ctx, args):
        if args:
            first_arg = args[0]
            if first_arg not in self.commands and not first_arg.startswith("-"):
                default_command = self.get_command(ctx, "roundtrip")
                if default_command is not None:
                    return "roundtrip", default_command, args

        return super().resolve_command(ctx, args)


app = typer.Typer(
    cls=DefaultToRoundtripGroup,
    help="PDFTwin: A developer-first tool to reconstruct and digitize PDFs.",
    no_args_is_help=True,
    epilog=(
        "Default usage: pdftwin input.pdf -o /tmp/output.pdf\n"
        "Roundtrip outputs /tmp/output.pdf and /tmp/output.json.\n"
        "If -o is omitted, outputs default to ./<input_stem>_twin.pdf and "
        "./<input_stem>_twin.json."
    ),
)
config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")


def _build_document_ir(input_pdf: str) -> Document:
    doc = fitz.open(input_pdf)
    try:
        agent = OrchestratorAgent()
        result = agent.run(doc)
    finally:
        doc.close()

    return Document(pages=result["pages"], metadata=result["metadata"], traces=result["traces"])


def _resolve_output_path(output: Optional[str], default_path: Path) -> Path:
    output_path = Path(output).expanduser() if output else default_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def _default_roundtrip_output(input_pdf: str) -> Path:
    return Path.cwd() / f"{Path(input_pdf).stem}_twin.pdf"


def _json_path_for_output(output_path: Path) -> Path:
    return output_path.with_suffix(".json")


def _write_document_ir(doc_ir: Document, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc_ir.model_dump_json(indent=2))


def _run_roundtrip(input_pdf: str, output: Optional[str] = None) -> None:
    if not os.path.exists(input_pdf):
        typer.echo(f"Error: {input_pdf} not found.", err=True)
        sys.exit(1)

    doc_ir = _build_document_ir(input_pdf)
    pdf_output_path = _resolve_output_path(output, _default_roundtrip_output(input_pdf))
    json_output_path = _json_path_for_output(pdf_output_path)

    _write_document_ir(doc_ir, json_output_path)
    PdfRenderer.render(doc_ir, str(pdf_output_path))

    typer.echo(f"PDF output: {pdf_output_path}")
    typer.echo(f"JSON output: {json_output_path}")
    typer.echo(f"Successfully roundtripped {input_pdf}")


@app.command()
def extract(
    input_pdf: str,
    out_dir: str = typer.Option("/tmp", "--out-dir", "-d", help="Output directory"),
    output: str = typer.Option("twin.json", "-o", "--output", help="Output IR JSON file"),
    model: str = typer.Option(config.model, help="LLM model to use"),
    use_llm: bool = typer.Option(config.use_llm, help="Enable or disable LLM agent fallbacks"),
    debug: bool = typer.Option(config.debug, help="Enable debug mode"),
):
    """Parses an input PDF into an intermediate JSON representation (IR)."""
    if not os.path.exists(input_pdf):
        typer.echo(f"Error: {input_pdf} not found.", err=True)
        sys.exit(1)

    config.model = model
    config.use_llm = use_llm
    config.debug = debug

    doc = fitz.open(input_pdf)
    agent = OrchestratorAgent()
    result = agent.run(doc)

    doc_ir = Document(pages=result["pages"], metadata=result["metadata"], traces=result["traces"])

    output_path = os.path.join(out_dir, output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        f.write(doc_ir.model_dump_json(indent=2))

    typer.echo(f"Successfully extracted {input_pdf} to {output_path}")


@app.command()
def render(
    input_json: str,
    out_dir: str = typer.Option("/tmp", "--out-dir", "-d", help="Output directory"),
    output: str = typer.Option("output.pdf", "-o", "--output", help="Output PDF file"),
):
    """Regenerates a PDF from an intermediate representation JSON file."""
    if not os.path.exists(input_json):
        typer.echo(f"Error: {input_json} not found.", err=True)
        sys.exit(1)

    with open(input_json, "r") as f:
        data = f.read()

    doc_ir = Document.model_validate_json(data)

    output_path = os.path.join(out_dir, output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    PdfRenderer.render(doc_ir, output_path)

    typer.echo(f"Successfully rendered {input_json} to {output_path}")


@app.command(hidden=True)
def roundtrip(
    input_pdf: str,
    output: Optional[str] = typer.Option(
        None,
        "-o",
        "--output",
        help="Output PDF path. Defaults to ./<input_stem>_twin.pdf.",
    ),
):
    """Extracts a PDF to IR and immediately renders it back to a new PDF."""
    _run_roundtrip(input_pdf, output)


@app.command()
def diff(
    original: str,
    recreated: str,
    out_dir: str = typer.Option("/tmp", "--out-dir", "-d", help="Output directory"),
    report: str = typer.Option("report.md", "--report", help="Output markdown report file"),
    images_dir: Optional[str] = typer.Option(
        None, "--images", help="Output directory for visual diff artifacts"
    ),
):
    """Compares the original PDF and the regenerated PDF visually."""
    if not os.path.exists(original) or not os.path.exists(recreated):
        typer.echo("Error: Both original and recreated PDFs must exist.", err=True)
        sys.exit(1)

    report_path = os.path.join(out_dir, report)
    images_path = os.path.join(out_dir, images_dir) if images_dir else None

    typer.echo(f"Comparing {original} and {recreated}...")
    results = compare_pdfs(original, recreated, out_dir=images_path)

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(f"# Diff Report: {original} vs {recreated}\n\n")
        if "error" in results:
            f.write(f"**Error**: {results['error']}\n")
        else:
            for pr in results["pages"]:
                f.write(f"## Page {pr['page']}\n")
                f.write(
                    f"- Deterministic Pixel Difference: {pr['deterministic_diff_percentage']:.2f}%\n"
                )
                if "vl_findings" in pr:
                    f.write("### Visual Verify Agent Findings\n")
                    f.write("```json\n")
                    f.write(json.dumps(pr["vl_findings"], indent=2))
                    f.write("\n```\n\n")

    typer.echo(f"Report saved to {report_path}")


@app.command()
def inspect(input_pdf: str):
    """Inspects a PDF and prints high-level statistics."""
    doc = fitz.open(input_pdf)
    typer.echo(f"File: {input_pdf}")
    typer.echo(f"Pages: {len(doc)}")
    typer.echo(f"Metadata: {doc.metadata}")


@app.command("agents")
def agents_trace(input_pdf: str):
    """Runs extraction and prints agent execution traces."""
    doc = fitz.open(input_pdf)
    agent = OrchestratorAgent()
    result = agent.run(doc)

    for trace in result["traces"]:
        typer.echo(f"[{trace.agent_id}] {trace.action}: {trace.status} ({trace.timestamp})")


@config_app.command("show")
def config_show():
    """Shows the current configuration settings."""
    typer.echo(config.model_dump_json(indent=2))


@config_app.command("init")
def config_init():
    """Initializes a new configuration file."""
    typer.echo("Config initialization not yet implemented. Use env vars like PDFTWIN_MODEL.")


if __name__ == "__main__":
    app()
