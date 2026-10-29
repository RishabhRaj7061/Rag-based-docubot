
import json
import uuid
from pathlib import Path

from backend.services.pdf_service import extract_text_from_pdf, chunk_pages
from backend.services.vector_service import save_document_vectors

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
INDEX_DIR = BASE_DIR / "data" / "indexes"
METADATA_FILE = BASE_DIR / "data" / "documents.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)


def load_documents() -> list[dict]:
    if not METADATA_FILE.exists():
        return []

    try:
        return json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_documents(documents: list[dict]) -> None:
    METADATA_FILE.write_text(
        json.dumps(documents, indent=2),
        encoding="utf-8",
    )


def process_pdf_file(filename: str, content: bytes) -> dict:
    """Save a PDF, extract text, create embeddings, and record metadata."""
    document_id = str(uuid.uuid4())
    safe_filename = Path(filename).name

    if not safe_filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF files are allowed.")

    pdf_path = UPLOAD_DIR / f"{document_id}.pdf"
    pdf_path.write_bytes(content)

    try:
        # Extract text and split it into chunks.
        pages = extract_text_from_pdf(str(pdf_path))
        chunks = chunk_pages(pages)

        if not chunks:
            raise ValueError(
                "No readable text found. The PDF may be scanned or image-only."
            )

        # Generate embeddings and save the FAISS index.
        vector_info = save_document_vectors(document_id, chunks)

        # Save document metadata.
        document = {
            "document_id": document_id,
            "filename": safe_filename,
            "stored_filename": pdf_path.name,
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "embedding_dimensions": vector_info["embedding_dimensions"],
            "status": "uploaded",
        }

        documents = load_documents()
        documents.append(document)
        save_documents(documents)

        return {
            **document,
            "pages_with_text": len(pages),
            "vectors_created": vector_info["vectors_created"],
        }

    except Exception:
        # Remove files created for this failed upload.
        pdf_path.unlink(missing_ok=True)
        (INDEX_DIR / f"{document_id}.faiss").unlink(missing_ok=True)
        (INDEX_DIR / f"{document_id}_chunks.json").unlink(missing_ok=True)
        raise
