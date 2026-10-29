
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from ordinary PDFs.
    Use OCR for pages without selectable text.
    Returns one dictionary per page.
    """
    extracted_pages = []
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with pymupdf.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            if not text:
                pix = page.get_pixmap(
                    matrix=pymupdf.Matrix(1.5, 1.5),
                    alpha=False,
                )
                image = None
                try:
                    image = Image.frombytes(
                        "RGB",
                        [pix.width, pix.height],
                        pix.samples,
                    )
                    text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                    ).strip()
                finally:
                    if image is not None:
                        image.close()

            extracted_pages.append({
                "page_number": page_number,
                "content": text,
            })

    return extracted_pages


def chunk_pages(
    pages: list[dict],
    filename: str = "Unknown document",
    document_id: str = "",
) -> list[dict]:
    """
    Split extracted page text into chunks for embedding.
    Supports page dictionaries containing 'content' or 'text'.
    """
    if not pages:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""],
    )

    chunks = []

    for page in pages:
        page_number = page.get("page_number", 1)
        page_text = page.get("content") or page.get("text") or ""

        if not isinstance(page_text, str) or not page_text.strip():
            continue

        for part in text_splitter.split_text(page_text.strip()):
            chunks.append({
                "text": part,
                "document_id": str(document_id),
                "filename": filename,
                "page_number": page_number,
            })

    return chunks
