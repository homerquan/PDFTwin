import os
from typing import Optional
from pydantic import BaseModel


class AppConfig(BaseModel):
    model: str = "gemini/gemini-3-flash-preview"
    provider: str = "gemini"
    api_base: Optional[str] = None
    use_llm: bool = True
    use_vl_review: bool = True
    ocr_mode: str = "auto"
    confidence_threshold: float = 0.8
    debug: bool = False


def load_config() -> AppConfig:
    return AppConfig(
        model=os.getenv("PDFTWIN_MODEL", "gemini/gemini-3-flash-preview"),
        use_llm=os.getenv("PDFTWIN_USE_LLM", "true").lower() == "true",
        debug=os.getenv("PDFTWIN_DEBUG", "false").lower() == "true",
        ocr_mode=os.getenv("PDFTWIN_OCR_MODE", "auto"),
    )


config = load_config()
