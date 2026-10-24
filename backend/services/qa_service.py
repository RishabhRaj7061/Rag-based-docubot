
from backend.services.search_service import search_documents
from backend.services.llm_services import generate_answer


def ask_document(
    question: str,
    document_id: str,
    top_k: int = 5,
) -> dict:
    results = search_documents(
        document_id=document_id,
        query=question,
        k=top_k,
    )

    if not results:
        raise ValueError("No relevant text was found in this document.")

    context_parts = []
    sources = []

    for item in results:
        context_parts.append(
            f"Page {item.get('page_number', 'Unknown')}:\n"
            f"{item.get('text', '')}"
        )
        sources.append({
            "page": item.get("page_number", "Unknown"),
            "text": item.get("text", ""),
            "filename": item.get("filename"),
        })

    context = "\n\n".join(context_parts)
    answer = generate_answer(question, context)

    return {
        "answer": answer,
        "sources": sources,
    }
