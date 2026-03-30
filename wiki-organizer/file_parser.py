"""Extract plain text from supported upload formats."""

from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from pypdf import PdfReader


class FileParseError(Exception):
    pass


def extract_text(filename: str, raw_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".md" or suffix == ".txt":
        return _decode_text(raw_bytes)
    if suffix == ".docx":
        return _extract_docx(raw_bytes)
    if suffix == ".pdf":
        return _extract_pdf(raw_bytes)
    raise FileParseError(f"Unsupported file type: {suffix}")


def _decode_text(raw_bytes: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return raw_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def _extract_docx(raw_bytes: bytes) -> str:
    doc = Document(io.BytesIO(raw_bytes))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(parts).strip() or "(empty document)"


def _extract_pdf(raw_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw_bytes))
    texts: list[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            texts.append(t)
    return "\n\n".join(texts).strip() or "(no extractable text in PDF)"
