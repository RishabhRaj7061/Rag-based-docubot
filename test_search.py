
from backend.services.document_service import load_documents
from backend.services.vector_service import search_documents

documents = load_documents()

if not documents:
    print("No documents found. Upload a PDF first.")
    raise SystemExit(1)

for document in documents:
    print(f"\nSearching document: {document['filename']}")

    results = search_documents(
        query="What is this document about?",
        document_id=document["document_id"],
        top_k=3,
    )

    if not results:
        print("No matching passages found.")
        continue

    for i, result in enumerate(results, start=1):
        print(f"\n--- Result {i} ---")
        print(f"Page: {result['page']}")
        print(f"Similarity score: {result['score']:.3f}")
        print(result["text"])
