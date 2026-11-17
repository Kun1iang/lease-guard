from __future__ import annotations

import io

import pymupdf
from docx import Document as DocxDocument

from app.parsers import parse_docx, parse_pdf


def test_parse_text_pdf_from_memory():
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Residential lease contract. Monthly rent is 3200 CNY.")
    data = document.tobytes()

    parsed = parse_pdf(data)

    assert len(parsed.pages) == 1
    assert "Residential lease contract" in parsed.pages[0].text
    assert parsed.ocr_used is False


def test_parse_docx_from_memory():
    document = DocxDocument()
    document.add_paragraph("住宅租赁合同")
    document.add_paragraph("月租金为人民币 3200 元。")
    buffer = io.BytesIO()
    document.save(buffer)

    parsed = parse_docx(buffer.getvalue())

    assert len(parsed.pages) == 1
    assert "住宅租赁合同" in parsed.pages[0].text
