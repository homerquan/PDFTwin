# IR Schema

The Intermediate Representation is the backbone of PDFTwin. It's defined using Pydantic, ensuring type safety and straightforward JSON serialization/deserialization.

## Core Models

### `Document`
Top-level object. Contains:
- `metadata`: Document title, author, producer.
- `pages`: List of `Page` objects.
- `traces`: Agent execution traces for debugging.

### `Page`
Represents a single PDF page.
- `width`, `height`
- `text_blocks`: List of grouped text.
- `images`: Extracted rasters.
- `vectors`: Drawing paths.
- `tables`: Detected tabular structures.

### `TextBlock` -> `TextLine` -> `TextSpan`
Text hierarchy:
- **Block**: Contains lines.
- **Line**: Contains spans.
- **Span**: Represents atomic text with identical formatting (font, size, color, bbox).

### `BoundingBox`
- Absolute coordinates (x0, y0, x1, y1) relative to the top-left of the page in points (1/72 inch).

### `FontSpec`
- Describes font characteristics: name, size, bold, italic, color.
- Stores matching fallbacks (e.g., `matched_font` populated by `FontAgent`).

### Provenance and Confidence
Each layout object stores:
- `provenance`: Which agent generated it and how.
- `confidence`: Certainty score.
