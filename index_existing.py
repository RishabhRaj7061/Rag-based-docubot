
from backend.services.document_service import (
    UPLOAD_DIR,
    load_documents,
)
from backend.services.pdf_service import (
    extract_text_from_pdf,
    chunk_pages,
)
from backend.services.vector_service import save_document_vectors

documents = load_documents()

if not documents:
    print("No uploaded documents found.")
    raise SystemExit(1)

for document in documents:
    document_id = document["document_id"]
    filename = document["filename"]
    pdf_path = UPLOAD_DIR / document["stored_filename"]

    if not pdf_path.exists():
        print(f"PDF file not found: {pdf_path}")
        continue

    index_path = (
        UPLOAD_DIR.parent / "indexes" / f"{document_id}.faiss"
    )

    if index_path.exists():
        print(f"Already indexed: {filename}")
        continue

    print(f"\nIndexing: {filename}")

    pages = extract_text_from_pdf(str(pdf_path))
    chunks = chunk_pages(pages)

    if not chunks:
        print("No readable text found. Skipping.")
        continue

    result = save_document_vectors(document_id, chunks)

    document["embedding_dimensions"] = result["embedding_dimensions"]
    document["status"] = "indexed"

    print(f"Chunks indexed: {result['vectors_created']}")
    print(f"Embedding dimensions: {result['embedding_dimensions']}")

from backend.services.document_service import save_documents
save_documents(documents)

print("\nIndexing process finished.")
