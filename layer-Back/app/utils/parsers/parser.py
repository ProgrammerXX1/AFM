# app/utils/parser.py

import fitz  # PyMuPDF

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    if filename.endswith(".pdf"):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)
    else:
        return file_bytes.decode("utf-8", errors="ignore")
