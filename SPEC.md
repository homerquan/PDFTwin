"""
# PDFTwin Specification

## Architecture
PDFTwin uses a multi-agent system to extract, understand, and recreate PDFs.

## Components
1. **IR Schema (Pydantic)**: Defines the structured intermediate representation.
2. **Agents**: Specialized modules (Layout, Text, Image, Vector, Font, OCR, VisualVerify, Orchestrator) that cooperatively build and verify the IR.
3. **LLM Gateway (LiteLLM)**: Handles routing to Gemini (or others) for complex visual/OCR tasks.
4. **Renderer**: Reconstructs the PDF from the IR.
5. **CLI**: The `pdftwin` command-line interface.

## Core Flow
`extract`: PDF -> PyMuPDF + Agents -> IR (JSON)
`render`: IR (JSON) -> PyMuPDF -> PDF
`pdftwin <input.pdf>`: PDF -> IR (JSON) + PDF
`diff`: Original PDF + Recreated PDF -> Pixel Diff + Vision LLM Report

## Dependencies
- PyMuPDF (fitz) for deterministic extraction and rendering
- LiteLLM for LLM abstractions
- Typer for CLI
- Pydantic for schemas
