from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_pages(
    pages: list[dict],
    filename: str,
    document_id: str,
) -> list[dict]:
    """
    Split extracted PDF page text into smaller chunks.
    Supports page dictionaries containing either 'content' or 'text'.
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

        # pdf_service.py returns 'content', but support 'text' too.
        page_text = page.get("content") or page.get("text") or ""

        if not isinstance(page_text, str) or not page_text.strip():
            continue

        text_parts = text_splitter.split_text(page_text.strip())

        for part in text_parts:
            chunks.append(
                {
                    "text": part,
                    "document_id": str(document_id),
                    "filename": filename,
                    "page_number": page_number,
                }
            )

    return chunks