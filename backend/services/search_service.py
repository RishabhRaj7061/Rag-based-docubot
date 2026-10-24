
import json
from pathlib import Path

import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parents[2]
INDEX_DIR = BASE_DIR / "data" / "indexes"


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


def search_documents(
    document_id: str,
    query: str,
    k: int = 3,
) -> list[dict]:
    index_path = INDEX_DIR / document_id

    # New format: a LangChain FAISS directory.
    if index_path.is_dir():
        store = FAISS.load_local(
            str(index_path),
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
        results = store.similarity_search_with_score(query, k=k)
        return [
            {
                "text": doc.page_content,
                "filename": doc.metadata.get("filename"),
                "page_number": doc.metadata.get(
                    "page_number", doc.metadata.get("page", "Unknown")
                ),
                "score": float(score),
            }
            for doc, score in results
        ]

    # Legacy format: a standalone FAISS index plus chunks JSON.
    faiss_file = INDEX_DIR / f"{document_id}.faiss"
    chunks_file = INDEX_DIR / f"{document_id}_chunks.json"

    if not faiss_file.is_file() or not chunks_file.is_file():
        raise FileNotFoundError(
            f"Index files are missing for document {document_id}"
        )

    index = faiss.read_index(str(faiss_file))
    chunks = json.loads(chunks_file.read_text(encoding="utf-8"))

    if not chunks:
        return []

    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(query)
    import numpy as np

    vector = np.asarray([query_vector], dtype="float32")
    distances, indices = index.search(vector, min(k, len(chunks)))

    results = []
    for distance, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(chunks):
            continue
        chunk = chunks[idx]
        results.append({
            "text": chunk.get("text", ""),
            "filename": chunk.get("filename"),
            "page_number": chunk.get(
                "page_number", chunk.get("page", "Unknown")
            ),
            "score": float(distance),
        })

    return results
