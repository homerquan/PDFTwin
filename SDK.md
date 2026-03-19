# PDFTwin SDK

`pdftwin` includes a Python SDK for apps that want to call PDFTwin directly instead of shelling out to the CLI.

This SDK is the recommended integration surface for:

- Python backends
- worker jobs
- internal tools
- web services built on top of PDFTwin

## Install

From PyPI:

```bash
pip install pdftwin
```

From source:

```bash
python3 -m pip install -e .
```

## Quick Start

```python
from pdftwin import replicate_pdf

result = replicate_pdf("input.pdf", "/tmp", use_llm=False)

print(result.output_pdf)
print(result.output_json)
```

This creates:

- `/tmp/input_twin.pdf`
- `/tmp/input_twin.json`

## Public SDK Functions

Import from `pdftwin`:

```python
from pdftwin import (
    diff_pdfs,
    extract_pdf,
    load_document,
    render_document,
    render_json,
    replicate_pdf,
    save_document,
)
```

### `extract_pdf`

Extract a PDF into PDFTwin's structured `Document` model.

```python
from pdftwin import extract_pdf

document = extract_pdf("contract.pdf", use_llm=False)
print(len(document.pages))
```

Arguments:

- `input_pdf`: PDF file path
- `model`: optional LLM model override
- `use_llm`: enable or disable LLM-assisted extraction
- `debug`: enable debug mode

Returns:

- `Document`

### `save_document`

Save a `Document` to JSON.

```python
from pdftwin import extract_pdf, save_document

document = extract_pdf("contract.pdf", use_llm=False)
json_path = save_document(document, "/tmp/contract_twin.json")
print(json_path)
```

Returns:

- resolved `Path` to the written JSON file

### `load_document`

Load a PDFTwin JSON file into a `Document`.

```python
from pdftwin import load_document

document = load_document("/tmp/contract_twin.json")
print(document.metadata.title)
```

Returns:

- `Document`

### `render_document`

Render a `Document` object to a PDF.

```python
from pdftwin import extract_pdf, render_document

document = extract_pdf("contract.pdf", use_llm=False)
result = render_document(document, "/tmp/recreated.pdf")
print(result.output_pdf)
```

Returns:

- `RenderResult`

Fields:

- `output_pdf`

### `render_json`

Render a JSON file directly to a PDF.

```python
from pdftwin import render_json

result = render_json("/tmp/contract_twin.json", "/tmp/recreated.pdf")
print(result.output_pdf)
```

Returns:

- `RenderResult`

### `replicate_pdf`

Create both the editable JSON and the replica PDF from one source PDF.

```python
from pdftwin import replicate_pdf

result = replicate_pdf("contract.pdf", "/tmp", use_llm=False)

print(result.output_pdf)
print(result.output_json)
print(result.document.pages[0].width)
```

Returns:

- `ReplicationResult`

Fields:

- `source_pdf`
- `output_pdf`
- `output_json`
- `document`

Output naming:

- `contract.pdf` becomes `contract_twin.pdf`
- `contract.pdf` becomes `contract_twin.json`

### `diff_pdfs`

Compare an original PDF and a recreated PDF.

```python
from pdftwin import diff_pdfs

result = diff_pdfs(
    "contract.pdf",
    "/tmp/contract_twin.pdf",
    dpi=300,
)

print(result.summary)
print(result.pages[0]["deterministic_diff_percentage"])
```

Returns:

- `DiffResult`

Fields:

- `original_pdf`
- `recreated_pdf`
- `pages`
- `summary`
- `raw_result`

## Common Integration Patterns

### 1. Extract, edit JSON, then render again

```python
from pdftwin import extract_pdf, render_document

document = extract_pdf("input.pdf", use_llm=False)
document.pages[0].text_blocks[0].lines[0].spans[0].text = "Updated title"
render_document(document, "/tmp/updated.pdf")
```

### 2. Build a web API on top of PDFTwin

```python
from pdftwin import replicate_pdf

def handle_upload(input_pdf_path: str, output_dir: str) -> dict:
    result = replicate_pdf(input_pdf_path, output_dir, use_llm=False)
    return {
        "pdf": str(result.output_pdf),
        "json": str(result.output_json),
    }
```

### 3. Use JSON as an editable document format

```python
from pdftwin import load_document, save_document

document = load_document("/tmp/input_twin.json")
document.metadata.author = "Homer Quan"
save_document(document, "/tmp/input_twin_edited.json")
```

## Data Model

The main SDK model is `Document`, defined in [src/pdftwin/models.py](/Users/homer/Personal_Projects/PDFTwin/src/pdftwin/models.py).

Key nested types include:

- `Document`
- `Page`
- `TextBlock`
- `TextLine`
- `TextSpan`
- `ImageObject`
- `VectorPath`
- `TableObject`

These are Pydantic models, so they support:

- `model_dump()`
- `model_dump_json()`
- `model_validate()`
- `model_validate_json()`

## Error Behavior

The SDK raises normal Python exceptions instead of exiting the process:

- missing files raise `FileNotFoundError`
- invalid JSON raises Pydantic validation errors
- rendering/extraction errors bubble up normally

This makes the SDK safer for web apps and job systems than invoking the CLI.

## Notes And Limits

- The SDK is Python-first. If you need cross-language access later, build an HTTP API on top of it.
- Some difficult PDFs still use raster fallback for visually faithful recreation.
- When a page uses raster fallback, edits may be partly overlay-based rather than a full vector rebuild.
- For best quality on difficult pages, regenerate the JSON with the latest PDFTwin version before rendering it again.

## Recommendation

If another app needs to integrate with PDFTwin, start with the SDK first.

- Use the SDK for in-process Python apps
- Add an HTTP API if you need cross-language or remote access
- Add MCP later only if you specifically want agent-facing tools
