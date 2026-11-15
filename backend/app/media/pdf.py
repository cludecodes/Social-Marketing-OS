"""Minimal PDF writer for downloadable lead-magnet guides (no external deps)."""
from __future__ import annotations

from pathlib import Path


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(path: Path, title: str, lines: list[str]) -> str:
    """Builds a simple single/multi-page text PDF with Helvetica."""
    pages: list[list[str]] = []
    current: list[str] = []
    for ln in lines:
        if len(current) >= 44:
            pages.append(current); current = []
        current.append(ln)
    if current or not pages:
        pages.append(current)

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    # Reserve: 1 catalog, 2 pages tree, then per page: page + content
    add(b"")
    add(b"")
    page_ids = []
    content_ids = []
    for _ in pages:
        page_ids.append(add(b""))
        content_ids.append(add(b""))
    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    kids = b" ".join(str(i).encode() + b" 0 R" for i in page_ids)
    objects[1] = b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(page_ids)).encode() + b" >>"
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"

    for idx, lines_page in enumerate(pages):
        content = b"BT /F1 11 Tf 50 800 Td 16 TL\n"
        first = True
        for ln in lines_page:
            txt = _pdf_escape(ln).encode("latin-1", "replace")
            if first:
                content += b"(" + txt + b") Tj\n"
                first = False
            else:
                content += b"T* (" + txt + b") Tj\n"
        content += b"ET"
        objects[content_ids[idx]] = b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream"
        objects[page_ids[idx]] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                                  b"/Resources << /Font << /F1 " + str(font_id).encode() + b" 0 R >> >> "
                                  b"/Contents " + str(content_ids[idx]).encode() + b" 0 R >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    Path(path).write_bytes(bytes(out))
    return str(path)
