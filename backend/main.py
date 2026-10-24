import json

import logging
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from docx import Document as WordDocument
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.services.document_service import (
    INDEX_DIR,
    UPLOAD_DIR,
    load_documents,
    save_documents,
    process_pdf_file,
)
from backend.services.pdf_service import chunk_pages
from backend.services.vector_service import save_document_vectors
from backend.services.qa_service import ask_document

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Based Docubot",
    description="Upload PDF and Word documents, then ask questions using RAG.",
    version="1.0.0",
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


def extract_docx_text(file_path: Path) -> list[dict]:
    """Extract paragraphs and tables from a Word DOCX file."""
    doc = WordDocument(str(file_path))
    parts = []

    for paragraph in doc.paragraphs:
        value = paragraph.text.strip()
        if value:
            parts.append(value)

    for table in doc.tables:
        for row in table.rows:
            values = [cell.text.strip() for cell in row.cells]
            line = " | ".join(value for value in values if value)
            if line:
                parts.append(line)

    text = "\n".join(parts).strip()
    return [{"page": 1, "text": text}] if text else []


def convert_doc_to_docx(file_path: Path, output_dir: Path) -> Path:
    """Convert legacy DOC files using LibreOffice."""
    executable = shutil.which("libreoffice") or shutil.which("soffice")

    if not executable:
        raise ValueError(
            "Legacy .doc files require LibreOffice. Install it or save "
            "the file as .docx and upload it again."
        )

    result = subprocess.run(
        [
            executable,
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(file_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    converted = output_dir / f"{file_path.stem}.docx"
    if result.returncode != 0 or not converted.exists():
        raise ValueError("Could not convert the DOC file to DOCX.")

    return converted


def process_word_file(filename: str, content: bytes) -> dict:
    """Save, extract, and index a Word document."""
    safe_filename = Path(filename).name
    extension = Path(safe_filename).suffix.lower()

    if extension not in {".docx", ".doc"}:
        raise ValueError("Only DOC and DOCX files are supported.")

    if not content:
        raise ValueError("The uploaded file is empty.")

    document_id = str(uuid.uuid4())
    stored_path = UPLOAD_DIR / f"{document_id}{extension}"
    index_path = UPLOAD_DIR.parent / "indexes" / f"{document_id}.faiss"
    chunks_path = (
        UPLOAD_DIR.parent / "indexes" / f"{document_id}_chunks.json"
    )

    stored_path.write_bytes(content)

    try:
        if extension == ".docx":
            pages = extract_docx_text(stored_path)
        else:
            with tempfile.TemporaryDirectory() as temp_dir:
                converted = convert_doc_to_docx(
                    stored_path, Path(temp_dir)
                )
                pages = extract_docx_text(converted)

        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No readable text was found in the Word file.")

        vector_info = save_document_vectors(document_id, chunks)

        metadata = {
            "document_id": document_id,
            "filename": safe_filename,
            "stored_filename": stored_path.name,
            "page_count": len(pages),
            "chunk_count": len(chunks),
            "embedding_dimensions": vector_info["embedding_dimensions"],
            "status": "indexed",
        }

        documents = load_documents()
        documents.append(metadata)
        save_documents(documents)

        return {
            **metadata,
            "pages_with_text": len(pages),
            "vectors_created": vector_info["vectors_created"],
        }

    except Exception:
        stored_path.unlink(missing_ok=True)
        index_path.unlink(missing_ok=True)
        chunks_path.unlink(missing_ok=True)
        raise


@app.get("/")
def home():
    return {
        "message": "Welcome to RAG Based Docubot!",
        "status": "running",
        "supported_formats": [".pdf", ".docx", ".doc"],
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "project": "RAG Based Docubot"}


@app.post("/documents/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    results = []
    errors = []

    for file in files:
        filename = file.filename or "document"
        extension = Path(filename).suffix.lower()

        try:
            if extension not in ALLOWED_EXTENSIONS:
                raise ValueError("Upload a PDF, DOCX, or DOC file.")

            content = await file.read()
            if not content:
                raise ValueError("The uploaded file is empty.")

            if extension == ".pdf":
                result = process_pdf_file(filename, content)
            else:
                result = process_word_file(filename, content)

            results.append(result)

        except Exception as exc:
            logger.exception("Failed to process uploaded file: %s", filename)
            errors.append({"filename": filename, "error": str(exc)})

        finally:
            await file.close()

    if not results:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No documents were processed successfully.",
                "errors": errors,
            },
        )

    return {
        "message": "Document upload and indexing completed.",
        "total_documents": len(results),
        "documents": results,
        "errors": errors,
    }


@app.get("/documents")
def list_documents():
    return {"documents": load_documents()}


@app.post("/ask")
def ask_question(request: QuestionRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty.",
        )

    document = next(
        (
            item for item in load_documents()
            if item.get("document_id") == request.document_id
        ),
        None,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found. Upload or index it first.",
        )

    try:
        return ask_document(
            question=question,
            document_id=request.document_id,
            top_k=request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Question answering failed")
        raise HTTPException(
            status_code=502,
            detail=(
                "Question answering failed. Check the backend terminal, "
                "Groq API key, model settings, and network connection."
            ),
        ) from exc


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Remove a document, its metadata, uploaded file, and vector indexes."""
    documents = load_documents()

    target = next(
        (doc for doc in documents
         if str(doc.get("id") or doc.get("document_id") or "") == document_id),
        None,
    )

    if target is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove the metadata entry first.
    remaining = [
        doc for doc in documents
        if str(doc.get("id") or doc.get("document_id") or "") != document_id
    ]
    save_documents(remaining)

    # Remove only files associated with this document ID.
    upload_dir = UPLOAD_DIR.resolve()
    index_dir = INDEX_DIR.resolve()

    for item in UPLOAD_DIR.glob(f"{document_id}.*"):
        try:
            if item.is_file() and item.resolve().parent == upload_dir:
                item.unlink()
        except OSError:
            pass

    # Legacy index files.
    for item in (
        INDEX_DIR / f"{document_id}.faiss",
        INDEX_DIR / f"{document_id}_chunks.json",
    ):
        try:
            if item.is_file() and item.resolve().parent == index_dir:
                item.unlink()
        except OSError:
            pass

    # Current LangChain index folder.
    current_index = (INDEX_DIR / document_id).resolve()
    if current_index.parent == index_dir and current_index.is_dir():
        shutil.rmtree(current_index)

    return {
        "message": "Document deleted successfully",
        "document_id": document_id,
    }
