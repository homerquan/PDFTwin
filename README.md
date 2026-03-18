# PDFTwin

PDFTwin is a developer-first CLI tool designed to reconstruct any PDF into a structured, editable Intermediate Representation (IR) and then seamlessly regenerate a visually matching PDF that is as close to pixel-perfect as possible.

**Why not just OCR?**
OCR gives you text. PDFTwin gives you a digital-twin document with editable structure—including text blocks, reading order, vector graphics, image placements, colors, layout relations, and an agent trace. This isn't just extraction; it's a true round-trip parser.

**Key Architecture**
PDFTwin uses a modular **Multi-Agent** approach. Each agent focuses on a particular slice of the problem (e.g., text, layouts, images, vectors, fonts), and an Orchestrator manages their lifecycle.

## Features
- Complete multi-agent architecture
- Configurable extraction (PyMuPDF backbone)
- JSON IR model that perfectly records PDF layout geometry
- Built-in font-matching agent to substitute unavailable fonts
- Generative AI integrations (Gemini via LiteLLM) for visual verification and difficult OCR.
- Detailed visual comparison metrics and structured reporting.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourname/pdftwin.git
cd pdftwin

# Install with development dependencies
pip install -e .[dev]

# Set up your environment for Gemini (LiteLLM requires this)
export GEMINI_API_KEY="your-google-gemini-key"
```

### Build For PyPI
```bash
python3 -m pip install -e .[dev]
python3 -m build
python3 -m twine check dist/*
```

To publish after building:
```bash
python3 -m twine upload dist/*
```

### Optional Extras
For advanced visual diffing capabilities, ensure you have system-level libraries suitable for Pillow (like libjpeg, zlib).

## Usage

### Extract PDF to Intermediate Representation (IR)
```bash
pdftwin extract input.pdf -o twin.json
```

### Render PDF from IR
```bash
pdftwin render twin.json -o recreated.pdf
```

### Default Roundtrip
```bash
pdftwin input.pdf -o /tmp/output.pdf
```

This roundtrip writes:
- PDF: `/tmp/output.pdf`
- JSON IR: `/tmp/output.json`

If you omit `-o`, PDFTwin writes:
- PDF: `./<input_stem>_twin.pdf`
- JSON IR: `./<input_stem>_twin.json`

### Inspect File
```bash
pdftwin inspect input.pdf
```

### Agent Traces
```bash
pdftwin agents input.pdf
```

### Diff original vs recreated
```bash
pdftwin diff input.pdf output.pdf --report diff_report.md --images diff_artifacts/
```

### Configuration
```bash
pdftwin config show
```

## Agent Roles
1. **Layout Agent**: Reconstructs reading order and geometric relationships.
2. **Text Agent**: Pulls out text, spans, fonts, weights, sizes.
3. **Image Agent**: Detects crops, rasters, placements.
4. **Vector Agent**: Paths, lines, draws.
5. **Font Agent**: Fallbacks and similarity.
6. **OCR / Vision Agent**: (LLM) Acts when standard extraction fails.
7. **Visual Verification Agent**: (LLM) "Does this page look the same?"

## Evaluation Stack
We evaluate PyMuPDF, pypdf, pdfplumber, etc. PyMuPDF was chosen for PDFTwin because it intrinsically returns deep layout geometries natively required for absolute coordinates reconstruction `get_text("dict")` and `get_drawings()`.

## Roadmap
- Deeper font metrics analysis via FreeType.
- Enhanced table detection via local heuristics.
- Improved non-linear reading order extraction.
