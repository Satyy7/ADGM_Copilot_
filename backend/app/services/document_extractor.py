"""Utility: extract plain text from uploaded PDF or DOCX bytes.

Used by the compliance review endpoint to convert a user-uploaded document
into a string the review agent pipeline can process.
"""

from __future__ import annotations

import io
from pathlib import Path


_MAX_CHARS: int = 8_000
"""Hard limit on text fed to the review agents.

Most ADGM compliance documents have their key clauses within the first 8000
characters.  Keeping the limit tight ensures prompts stay within token budgets
for both Gemini (free tier) and Groq.
"""


def extract_text(content: bytes, filename: str) -> str:
    """Extract plain text from PDF or DOCX bytes.

    Parameters
    ----------
    content:
        Raw file bytes from an uploaded file.
    filename:
        Original filename — used to determine the file format.

    Returns
    -------
    Extracted text, truncated to ``_MAX_CHARS`` characters.

    Raises
    ------
    ValueError
        If the file extension is not ``.pdf`` or ``.docx``.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        text = _extract_pdf(content)
    elif ext in (".docx", ".doc"):
        text = _extract_docx(content)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. Upload a PDF (.pdf) or Word document (.docx)."
        )
    return text[:_MAX_CHARS]


def _extract_pdf(content: bytes) -> str:
    import fitz  # PyMuPDF — already a project dependency

    with fitz.open(stream=content, filetype="pdf") as doc:
        pages = [page.get_text("text") for page in doc]
    return "\n".join(p for p in pages if p.strip())


def _extract_docx(content: bytes) -> str:
    from docx import Document  # python-docx — already a project dependency

    doc = Document(io.BytesIO(content))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)
