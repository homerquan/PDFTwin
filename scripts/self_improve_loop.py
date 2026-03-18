import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from pdftwin.agents.orchestrator import OrchestratorAgent
from pdftwin.comparison.diff import compare_pdfs
from pdftwin.config import config
from pdftwin.models import Document
from pdftwin.renderers.pdf_renderer import PdfRenderer

import fitz


def build_ir(input_pdf: Path) -> Document:
    doc = fitz.open(str(input_pdf))
    try:
        result = OrchestratorAgent().run(doc)
    finally:
        doc.close()
    return Document(pages=result["pages"], metadata=result["metadata"], traces=result["traces"])


def write_iteration_report(report_path: Path, report: Dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))


def summarize_page(page_report: Dict[str, Any]) -> Dict[str, Any]:
    vl = page_report.get("vl_findings") or {}
    return {
        "page": page_report["page"],
        "deterministic_diff_percentage": page_report["deterministic_diff_percentage"],
        "is_visually_identical": vl.get("is_visually_identical"),
        "differences_found": vl.get("differences_found", []),
        "text_issues": vl.get("text_issues", []),
        "table_issues": vl.get("table_issues", []),
        "image_issues": vl.get("image_issues", []),
        "text_corruption_detected": vl.get("text_corruption_detected"),
        "text_overflow_detected": vl.get("text_overflow_detected"),
    }


def iteration_has_issues(compare_report: Dict[str, Any]) -> bool:
    if compare_report.get("summary", {}).get("max_diff_percentage", 0.0) > 0.0:
        return True

    for page in compare_report.get("pages", []):
        vl = page.get("vl_findings") or {}
        if vl.get("error"):
            return True
        if vl.get("is_visually_identical") is False:
            return True
        if vl.get("differences_found"):
            return True
        if vl.get("text_issues"):
            return True
        if vl.get("table_issues"):
            return True
        if vl.get("image_issues"):
            return True
        if vl.get("text_corruption_detected"):
            return True
        if vl.get("text_overflow_detected"):
            return True

    return False


def run_iteration(input_pdf: Path, output_root: Path, iteration: int) -> Dict[str, Any]:
    iteration_dir = output_root / f"iteration_{iteration}"
    iteration_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{input_pdf.stem}_twin"
    pdf_out = iteration_dir / f"{stem}.pdf"
    json_out = iteration_dir / f"{stem}.json"

    doc_ir = build_ir(input_pdf)
    json_out.write_text(doc_ir.model_dump_json(indent=2))
    PdfRenderer.render(doc_ir, str(pdf_out))

    compare_report = compare_pdfs(
        str(input_pdf),
        str(pdf_out),
        out_dir=str(iteration_dir / "diff"),
        run_vl_on_all_pages=True,
    )

    report = {
        "iteration": iteration,
        "input_pdf": str(input_pdf),
        "output_pdf": str(pdf_out),
        "output_json": str(json_out),
        "summary": compare_report.get("summary", {}),
        "pages": [summarize_page(page) for page in compare_report.get("pages", [])],
        "has_issues": iteration_has_issues(compare_report),
    }
    write_iteration_report(iteration_dir / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run repeated PDFTwin generation + VL evaluation iterations."
    )
    parser.add_argument("input_pdf", help="Source PDF to evaluate.")
    parser.add_argument(
        "--iterations", type=int, default=5, help="Number of evaluation iterations to run."
    )
    parser.add_argument(
        "--output-root",
        default="/tmp/pdftwin-self-improve",
        help="Directory for generated outputs and reports.",
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Disable LLM-backed OCR and visual review.",
    )
    args = parser.parse_args()

    input_pdf = Path(args.input_pdf).resolve()
    output_root = Path(args.output_root).resolve()

    config.use_llm = not args.disable_llm
    config.use_vl_review = not args.disable_llm
    config.ocr_mode = "disabled"

    all_reports: List[Dict[str, Any]] = []
    for iteration in range(1, args.iterations + 1):
        report = run_iteration(input_pdf, output_root, iteration)
        all_reports.append(report)
        print(
            f"Iteration {iteration}: max_diff={report['summary'].get('max_diff_percentage', 0.0):.2f}% "
            f"issues={report['has_issues']}"
        )

    output_root.mkdir(parents=True, exist_ok=True)
    write_iteration_report(output_root / "summary.json", {"iterations": all_reports})

    return 1 if any(report["has_issues"] for report in all_reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
