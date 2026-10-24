
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parents[2]
INDEX_DIR = BASE_DIR / "data" / "indexes"
INDEX_DIR.mkdir(parents=True, exist_ok=True)


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


def save_document_vectors(document_id: str, chunks: list[dict]) -> dict:
    if not chunks:
        raise ValueError("No text chunks available to index.")

    texts = []
    metadatas = []

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if not text:
            continue

        texts.append(text)
        metadatas.append({
            "document_id": document_id,
            "filename": chunk.get("filename", "Unknown document"),
            "page_number": chunk.get(
                "page_number", chunk.get("page", 1)
            ),
        })

    if not texts:
        raise ValueError("No valid text chunks found.")

    vector_store = FAISS.from_texts(
        texts=texts,
        embedding=get_embeddings(),
        metadatas=metadatas,
    )

    index_path = INDEX_DIR / document_id
    vector_store.save_local(str(index_path))

    return {
        "vectors_created": len(texts),
        "embedding_dimensions": 384,
    }
