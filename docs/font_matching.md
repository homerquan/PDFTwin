# Font Matching Strategy

When rendering an extracted document to PDF, the exact embedded fonts are often not available system-wide or cannot be legally redistributed.

The `FontAgent` resolves missing fonts through a tiered fallback strategy to maintain layout fidelity.

## Heuristics

1. **Name Matching**:
   Does the PDF font contain "Times", "Serif", "Courier", or "Mono"?

2. **Weight/Style inference**:
   We parse bold/italic boolean indicators from `get_text("dict")` or name keywords (`-BoldItalic`, `Oblique`).
   
3. **Core 14 Fonts**:
   For the default PDF renderer (`fitz.Page.insert_text`), we map identified fonts to the "Standard 14" fonts built into all PDF viewers:
   - `Helvetica` (Default Sans)
   - `Times-Roman` (Default Serif)
   - `Courier` (Default Mono)
   - Variations (-Bold, -Oblique, -BoldOblique)

## Future Roadmap

To improve character spacing limits and metric calculations without relying on built-in standard fonts:
- Integrate `fontTools` to parse system font tables.
- Use font metrics like CapHeight, XHeight, Ascender, Descender for geometric matching.
