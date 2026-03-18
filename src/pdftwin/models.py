from typing import List, Optional, Any, Dict, Tuple
from pydantic import BaseModel, Field


class ConfidenceScore(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    agent_id: str
    rationale: Optional[str] = None


class Provenance(BaseModel):
    agent_id: str
    method: str
    original_element_id: Optional[str] = None


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class TransformMatrix(BaseModel):
    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0


class DrawingStyle(BaseModel):
    fill_color: Optional[Tuple[float, float, float]] = None
    stroke_color: Optional[Tuple[float, float, float]] = None
    stroke_width: Optional[float] = None
    stroke_opacity: float = 1.0
    fill_opacity: float = 1.0
    dashes: Optional[List[float]] = None


class FontSpec(BaseModel):
    name: str
    size: float
    is_bold: bool = False
    is_italic: bool = False
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    # the matching agent will populate these:
    matched_font: Optional[str] = None
    fallback_used: bool = False


class TextSpan(BaseModel):
    text: str
    bbox: BoundingBox
    origin: Optional[Tuple[float, float]] = None
    font: FontSpec
    provenance: Optional[Provenance] = None
    confidence: Optional[ConfidenceScore] = None


class TextLine(BaseModel):
    spans: List[TextSpan]
    bbox: BoundingBox
    dir: Tuple[float, float] = (1.0, 0.0)  # direction vector


class TextBlock(BaseModel):
    lines: List[TextLine]
    bbox: BoundingBox
    block_type: int = 0  # 0: text, 1: image/other
    provenance: Optional[Provenance] = None
    confidence: Optional[ConfidenceScore] = None


class ImageObject(BaseModel):
    bbox: BoundingBox
    width: int
    height: int
    image_base64: str
    transform: TransformMatrix = TransformMatrix()
    provenance: Optional[Provenance] = None
    confidence: Optional[ConfidenceScore] = None


class VectorPath(BaseModel):
    items: List[Tuple[str, Any]]  # e.g., ("l", (x, y)) for line
    style: DrawingStyle
    bbox: Optional[BoundingBox] = None
    provenance: Optional[Provenance] = None
    confidence: Optional[ConfidenceScore] = None


class TableCell(BaseModel):
    bbox: BoundingBox
    content: List[TextBlock] = []
    row_span: int = 1
    col_span: int = 1


class TableObject(BaseModel):
    bbox: BoundingBox
    cells: List[TableCell]
    provenance: Optional[Provenance] = None
    confidence: Optional[ConfidenceScore] = None


class Page(BaseModel):
    page_number: int
    width: float
    height: float
    text_blocks: List[TextBlock] = []
    images: List[ImageObject] = []
    vectors: List[VectorPath] = []
    tables: List[TableObject] = []


class Metadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None
    producer: Optional[str] = None


class AgentTrace(BaseModel):
    agent_id: str
    action: str
    status: str
    timestamp: float
    details: Optional[Dict[str, Any]] = None


class Document(BaseModel):
    metadata: Metadata = Metadata()
    pages: List[Page] = []
    traces: List[AgentTrace] = []
