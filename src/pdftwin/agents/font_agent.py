from typing import Any, Dict
from .base import BaseAgent


class FontAgent(BaseAgent):
    """Determines the closest available font if exact is missing."""

    def run(self, context: Any, **kwargs: Any) -> Dict[str, Any]:
        text_blocks: list = context
        traces = []
        traces.append(self.record_trace("start", "Font matching started"))

        # Simple local fallback logic for v1.
        # In a full system, you'd inspect local TTF/OTF files with fontTools here.

        for block in text_blocks:
            for line in block.lines:
                for span in line.spans:
                    font_name = span.font.name.lower()

                    if any(x in font_name for x in ["times", "serif", "roman", "cmr"]):
                        matched = "Times-Roman"
                    elif any(x in font_name for x in ["courier", "mono"]):
                        matched = "Courier"
                    else:
                        matched = "Helvetica"  # Default fallback

                    if span.font.is_bold and span.font.is_italic:
                        matched += "-BoldOblique" if matched == "Helvetica" else "-BoldItalic"
                    elif span.font.is_bold:
                        matched += "-Bold"
                    elif span.font.is_italic:
                        matched += "-Oblique" if matched == "Helvetica" else "-Italic"

                    span.font.matched_font = matched
                    span.font.fallback_used = span.font.name != matched

        traces.append(self.record_trace("success", "Font matching completed"))

        return {"text_blocks": text_blocks, "traces": traces}
