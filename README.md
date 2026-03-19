# PDFTwin

PDFTwin turns a PDF into files that are easier to work with:

- An editable JSON representation of the document
- A replica PDF that stays visually close to the original

This is useful when you want more than plain OCR text. PDFTwin keeps layout, text blocks, images, vectors, fonts, and page geometry so you can inspect, transform, compare, or regenerate the document.

## What You Get

Given a file like `invoice.pdf`, PDFTwin can create:

- `invoice_twin.json`
- `invoice_twin.pdf`

The JSON is the editable version. The PDF is the visual replica.

## Quick Start

After the package is published to PyPI:

```bash
pip install pdftwin
```

From the source repo today:

```bash
# clone this repository first
cd PDFTwin
python3 -m pip install -e .
```

If you want development tools too:

```bash
python3 -m pip install -e .[dev]
```

If you want to call PDFTwin from Python code directly, see `SDK.md`.

## Create Editable Outputs From a PDF

```bash
pdftwin input.pdf -o /tmp
```

This writes:

- `/tmp/input_twin.pdf`
- `/tmp/input_twin.json`

If you omit `-o`, PDFTwin writes both files to the current folder:

- `./input_twin.pdf`
- `./input_twin.json`

`-o` is an output folder, not a filename.

## Common Workflows

### 1. Create both editable JSON and a replica PDF

```bash
pdftwin contract.pdf -o ./outputs
```

This creates:

- `./outputs/contract_twin.json`
- `./outputs/contract_twin.pdf`

### 2. Create only the editable JSON

```bash
pdftwin extract contract.pdf -o contract_twin.json
```

### 3. Create a replica PDF from JSON

```bash
pdftwin render contract_twin.json -o recreated.pdf
```

### 4. Compare the original PDF with the replica PDF

```bash
pdftwin diff contract.pdf recreated.pdf --report diff_report.md --images diff_artifacts/
```

### 5. Inspect a PDF before processing

```bash
pdftwin inspect contract.pdf
```

## Why Use PDFTwin Instead Of Basic OCR

Basic OCR usually gives you text only.

PDFTwin is designed to preserve document structure such as:

- Page sizes and layout
- Text spans and positions
- Images and their placements
- Vector lines and shapes
- Font information and fallback matching

That makes it better suited for rebuilding documents, document analysis, migrations, validation, and automated processing pipelines.

## How It Works

PDFTwin extracts the PDF into a structured JSON model using PyMuPDF and a set of specialized agents. That JSON can then be used to create a replica PDF, inspect document structure, or compare output quality against the original.

For harder documents, the tool can optionally use LLM-assisted OCR and visual verification.

## Configuration

Show the current config:

```bash
pdftwin config show
```

If you plan to use Gemini-powered OCR or visual checks, set your API key:

```bash
export GEMINI_API_KEY="your-google-gemini-key"
```

## Automatic PyPI Publishing

This repository now includes GitHub Actions workflows for both CI and PyPI publishing:

- `.github/workflows/ci.yml` runs tests and validates the package build on pushes and pull requests
- `.github/workflows/publish.yml` publishes to PyPI with GitHub Trusted Publishing

### Trusted Publisher Settings

In PyPI, the trusted publisher should point to:

- Owner: `homerquan`
- Repository: `PDFTwin`
- Workflow file: `.github/workflows/publish.yml`
- Environment: `pypi`

### Release Flow

1. Update the version in `pyproject.toml` and `src/pdftwin/__init__.py`
2. Commit your changes
3. Create and push a version tag such as `v0.1.1`

```bash
git tag v0.1.1
git push origin v0.1.1
```

That tag triggers the publish workflow, which:

- verifies the tag matches the package version
- runs the test suite
- builds the wheel and source distribution
- publishes to PyPI using GitHub OIDC, without a saved PyPI API token

### Manual Build Fallback

If you ever want to build locally before releasing:

```bash
python3 -m build
python3 -m twine check dist/*
```

## Notes

- For advanced image diffing, your system should have common Pillow dependencies available, such as `libjpeg` and `zlib`.
- Some scanned PDFs may contain a full-page image plus a text layer. PDFTwin preserves searchability while avoiding duplicated visible text in the replica PDF.
