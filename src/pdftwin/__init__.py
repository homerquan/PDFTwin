__version__ = "0.1.0"

from .cli import app
from .sdk import (
    DiffResult,
    RenderResult,
    ReplicationResult,
    diff_pdfs,
    extract_pdf,
    load_document,
    render_document,
    render_json,
    replicate_pdf,
    save_document,
)

__all__ = [
    "app",
    "__version__",
    "DiffResult",
    "RenderResult",
    "ReplicationResult",
    "diff_pdfs",
    "extract_pdf",
    "load_document",
    "render_document",
    "render_json",
    "replicate_pdf",
    "save_document",
]
