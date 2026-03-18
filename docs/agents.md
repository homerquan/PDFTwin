# Agents

PDFTwin's capabilities are divided among modular agents.

## Core Extraction Agents

- **LayoutAgent**: Sorts elements and identifies reading order, headers, footers.
- **TextAgent**: Uses `PyMuPDF` `get_text("dict")` to extract spans, lines, and blocks with full styling (font, color, size) and positioning.
- **ImageAgent**: Uses `get_images()` and `extract_image()` to pull out rasters and encodes them in base64.
- **VectorAgent**: Uses `get_drawings()` to trace paths and vector styles.

## Processing Agents

- **FontAgent**: Analyzes extracted fonts against a target system or generic set to match weights, italics, and visual families.

## LLM / Vision Agents

- **OcrAgent**: Activated for scanned PDFs. Calls a configured LLM (e.g., Gemini) with instructions to perfectly transcribe text with spatial awareness.
- **VisualVerifyAgent**: Runs post-render. Takes the original PDF image and the rendered PDF image and compares them via a Vision model to score their similarity, verifying font mapping and layout decisions.

## Orchestration
- **OrchestratorAgent**: Ties everything together, handling page iterations and agent sequencing.
