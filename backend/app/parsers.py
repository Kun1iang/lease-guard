"""PDF, DOCX, text and image parsing with an optional OCR adapter."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from docx import Document as DocxDocument


@dataclass
class ParsedPage:
    page_no: int
    text: str
    ocr_confidence: float | None = None


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    ocr_used: bool


class OcrUnavailable(RuntimeError):
    pass


class RapidOcrAdapter:
    """Load the optional OCR dependency only when a page actually needs it."""

    _engine = None

    @classmethod
    def read(cls, image_bytes: bytes) -> tuple[str, float | None]:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise OcrUnavailable("OCR 组件未安装，请使用 uv sync --extra ocr") from exc
        if cls._engine is None:
            cls._engine = RapidOCR()
        result, _ = cls._engine(image_bytes)
        if not result:
            return "", None
        texts = [item[1] for item in result]
        scores = [float(item[2]) for item in result if len(item) > 2]
        return "\n".join(texts), (sum(scores) / len(scores) if scores else None)


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\x00", "").splitlines()]
    compact: list[str] = []
    for line in lines:
        if not line:
            if compact and compact[-1] != "":
                compact.append("")
            continue
        compact.append(line)
    return "\n".join(compact).strip()


def parse_pdf(data: bytes) -> ParsedDocument:
    document = pymupdf.open(stream=data, filetype="pdf")
    pages: list[ParsedPage] = []
    ocr_used = False
    for index, page in enumerate(document):
        text = _normalize_text(page.get_text("text"))
        confidence = None
        if len(re.sub(r"\s", "", text)) < 30:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            text, confidence = RapidOcrAdapter.read(pix.tobytes("png"))
            text = _normalize_text(text)
            ocr_used = True
        pages.append(ParsedPage(index + 1, text, confidence))
    return ParsedDocument(pages, ocr_used)


def parse_docx(data: bytes) -> ParsedDocument:
    document = DocxDocument(io.BytesIO(data))
    blocks: list[str] = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            blocks.append(" | ".join(cell.text for cell in row.cells))
    text = _normalize_text("\n".join(blocks))
    return ParsedDocument([ParsedPage(1, text)], False)


def parse_image(data: bytes) -> ParsedDocument:
    text, confidence = RapidOcrAdapter.read(data)
    return ParsedDocument([ParsedPage(1, _normalize_text(text), confidence)], True)


def parse_text(text: str) -> ParsedDocument:
    return ParsedDocument([ParsedPage(1, _normalize_text(text))], False)


def parse_upload(filename: str, mime_type: str, data: bytes) -> ParsedDocument:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf" or mime_type == "application/pdf":
        return parse_pdf(data)
    if suffix == ".docx":
        return parse_docx(data)
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return parse_image(data)
    if suffix in {".txt", ".md"} or mime_type.startswith("text/"):
        return parse_text(data.decode("utf-8-sig", errors="replace"))
    raise ValueError("UNSUPPORTED_FILE_TYPE")
