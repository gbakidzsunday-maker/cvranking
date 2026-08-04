"""
Resume Parsing and Pre-processing Module (Chapter 3.3, layer 2a)
------------------------------------------------------------------
Extracts raw text from uploaded resume files (PDF or DOCX) and cleans it
for downstream embedding generation.
"""
import re
import fitz  # PyMuPDF
import docx
from fastapi import HTTPException


def extract_text_from_pdf(file_path: str) -> str:
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def extract_text_from_docx(file_path: str) -> str:
    document = docx.Document(file_path)
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())


def extract_text(file_path: str, filename: str) -> str:
    """Dispatch to the correct extractor based on file extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        raw = extract_text_from_pdf(file_path)
    elif lower.endswith(".docx"):
        raw = extract_text_from_docx(file_path)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a PDF or DOCX resume.",
        )

    cleaned = clean_text(raw)
    if not cleaned.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "No extractable text found in the uploaded file. "
                "Scanned/image-based resumes are not supported."
            ),
        )
    return cleaned


def clean_text(text: str) -> str:
    """Remove excess whitespace and non-printable characters."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = "".join(ch for ch in text if ch.isprintable() or ch == "\n")
    return text.strip()
