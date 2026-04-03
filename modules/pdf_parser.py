"""PDF text extraction using PyMuPDF (fitz)."""

import fitz  # PyMuPDF


def extract_text_from_pdf(filepath: str) -> str:
    """Extract and clean text from all pages of a PDF file."""
    doc = fitz.open(filepath)
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()

    raw = "\n".join(pages)
    # Basic cleanup: collapse excessive blank lines
    lines = [line.strip() for line in raw.splitlines()]
    cleaned_lines = []
    prev_blank = False
    for line in lines:
        if line == "":
            if not prev_blank:
                cleaned_lines.append("")
            prev_blank = True
        else:
            cleaned_lines.append(line)
            prev_blank = False

    return "\n".join(cleaned_lines).strip()
