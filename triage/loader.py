"""Load demand content from various file formats.

- .txt, .md   -> UTF-8 text
- .docx       -> text extracted via python-docx (paragraphs + tables)
- .pdf        -> native Claude document block (full vision, handles scans)
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}

# Anthropic API limit for inline base64 PDF payloads.
_MAX_PDF_BYTES = 32 * 1024 * 1024


def load_demand(path: Path) -> str | list[dict[str, Any]]:
    """Load a demand file.

    Returns either:
      * `str` — plain text (for .txt, .md, .docx); feed to `TriageAgent.triage`.
      * `list[dict]` — a Claude content-block list (for .pdf) containing a
        `document` block; feed to `TriageAgent.triage_blocks`.

    Raises `ValueError` for unsupported extensions and `RuntimeError` when an
    optional dependency (python-docx) is missing.
    """
    ext = path.suffix.lower()
    if ext in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if ext == ".docx":
        return _extract_docx(path)
    if ext == ".pdf":
        return _pdf_blocks(path)
    raise ValueError(
        f"Unsupported file type: {path.suffix!r}. "
        f"Supported extensions: {sorted(SUPPORTED_EXTENSIONS)}"
    )


def _extract_docx(path: Path) -> str:
    try:
        import docx  # type: ignore[import-untyped]  # python-docx
    except ImportError as exc:
        raise RuntimeError(
            "python-docx is required to read .docx files. "
            "Install with: pip install python-docx"
        ) from exc

    document = docx.Document(str(path))

    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)

    for table in document.tables:
        parts.append("")
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            parts.append(" | ".join(cells))

    if not parts:
        raise ValueError(f"No text extracted from {path}")
    return "\n".join(parts).strip()


def _pdf_blocks(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    if len(data) > _MAX_PDF_BYTES:
        raise ValueError(
            f"PDF {path.name} is {len(data) / 1_000_000:.1f} MB; the inline "
            f"PDF limit is 32 MB. Split the document or use the Files API."
        )
    encoded = base64.standard_b64encode(data).decode("utf-8")
    return [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": encoded,
            },
            "title": path.name,
        }
    ]
