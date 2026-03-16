"""Retriever that wraps the DocumentStore and adds context formatting."""

from __future__ import annotations

from .document import Document
from .store import DocumentStore


class Retriever:
    """High-level retriever for the RAG pipeline.

    Wraps a DocumentStore and provides a method to retrieve and format
    context passages that can be injected into an LLM prompt.
    """

    def __init__(self, store: DocumentStore | None = None) -> None:
        self.store = store or DocumentStore()

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the underlying store."""
        self.store.add_documents(documents)

    def retrieve(self, query: str, k: int = 5) -> list[Document]:
        """Retrieve the top-k relevant documents for a given query."""
        return self.store.search(query, k=k)

    def retrieve_context(self, query: str, k: int = 5) -> str:
        """Return a formatted context string for injection into an LLM prompt.

        Args:
            query: The user question.
            k: Maximum number of documents to include.

        Returns:
            A plain-text block containing the retrieved passages, or an
            empty string if no relevant documents are found.
        """
        docs = self.retrieve(query, k=k)
        if not docs:
            return ""
        passages = "\n\n".join(
            f"[Fonte {i + 1}]\n{doc.content}" for i, doc in enumerate(docs)
        )
        return passages
