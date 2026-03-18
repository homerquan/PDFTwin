# Testing Strategy

PDFTwin relies on comprehensive automated tests to verify extraction fidelity, deterministic parsing, agent orchestration, and IR serialization.

## Test Environment Setup

```bash
# Install test dependencies
pip install -e .[dev]

# Run tests
pytest
```

## Layers of Testing

1. **Schema & Model Validation** (`test_models_serialization`):
   - Confirms that nested IR models dump and parse JSON flawlessly.
   - Verifies `TextSpan`, `BoundingBox`, and `Page` relations.

2. **Synthetic Generation & Extraction** (`test_extraction_orchestrator`):
   - Rather than checking in large PDF files, PyMuPDF generates simple synthetic PDFs (e.g., placing text at `x=50, y=50`) on the fly.
   - Extracts the synthetic document, validating that text coordinates are found at precisely `x=50`.

3. **Roundtrip Rendering** (`test_render_roundtrip`):
   - Extracts a synthetic PDF.
   - Feeds IR to `PdfRenderer`.
   - Opens the regenerated PDF to verify text placement and layout fidelity.

4. **CLI Flow** (`test_cli_roundtrip`, `test_cli_roundtrip_default_output`, `test_cli_config_show`):
   - Uses Typer's `CliRunner` to perform e2e tests simulating actual command-line invocations without invoking sub-processes directly.
   - Confirms the default `pdftwin <input.pdf>` roundtrip flow, PDF/JSON artifact paths, and configuration options.
