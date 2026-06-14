"""PDF text extraction via PyMuPDF — linear text (for the LLM) + block bboxes (provenance)."""
from __future__ import annotations

from dataclasses import dataclass, field

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - fitz is a hard dep, but keep import errors clear
    fitz = None


@dataclass
class PageText:
    page_index: int
    text: str
    is_text_page: bool  # True if enough extractable text; False -> needs OCR (Phase 3)
    blocks: list[dict] = field(default_factory=list)  # [{text, bbox:[x0,y0,x1,y1]}]


@dataclass
class PdfExtract:
    pages: list[PageText]

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"[page {p.page_index}]\n{p.text}" for p in self.pages)

    @property
    def has_text(self) -> bool:
        return any(p.is_text_page for p in self.pages)


# Heuristic: a page with fewer than this many characters is treated as a scan/image page.
TEXT_PAGE_MIN_CHARS = 40


def extract_pdf(path: str) -> PdfExtract:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed")

    pages: list[PageText] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            blocks = []
            for b in page.get_text("blocks") or []:
                # block tuple: (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5 and isinstance(b[4], str) and b[4].strip():
                    blocks.append({"text": b[4].strip(), "bbox": [b[0], b[1], b[2], b[3]]})
            pages.append(
                PageText(
                    page_index=i,
                    text=text,
                    is_text_page=len(text.strip()) >= TEXT_PAGE_MIN_CHARS,
                    blocks=blocks,
                )
            )
    return PdfExtract(pages=pages)
