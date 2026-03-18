# Architecture

PDFTwin handles document reconstruction by isolating distinct parsing concerns into independent Agents. The architecture is defined by three phases:

## 1. Extraction (PDF -> IR)
The Orchestrator agent takes a fitz (PyMuPDF) Document and iterates through pages.
It delegates text, vector, and image processing to specific agents.
These agents do not directly mutate each other's outputs. They produce lists of primitive typed schemas defined in `models.py`.

## 2. Enrichment & Processing
Once primitives are extracted, agents like the `FontAgent` and `LayoutAgent` step in.
- `FontAgent`: Maps specific PDF font metrics to closest matching standard fonts to ensure the Render phase won't fail to calculate layout limits.
- `LayoutAgent`: Takes disparate text blocks and infers geometric and semantic reading orders.

## 3. Rendering (IR -> PDF)
The Renderer phase (`PdfRenderer`) is a deterministic module. It uses `fitz` to recreate the document from the ground up, utilizing absolute positioning coordinates from the IR schemas.

## Gateway
We use `LiteLLM` to standardize LLM interactions. It routes requests, standardizes JSON output formatting for Pydantic schema validation, and allows model switching.
