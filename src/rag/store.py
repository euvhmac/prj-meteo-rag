"""TF-IDF based document store for RAG retrieval."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .document import Document


class DocumentStore:
    """In-memory document store with TF-IDF similarity search.

    Documents are indexed using scikit-learn's TF-IDF vectorizer.
    Retrieval is performed via cosine similarity between the query
    and all stored document embeddings.
    """

    def __init__(self) -> None:
        self._documents: list[Document] = []
        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b",
            sublinear_tf=True,
        )
        self._matrix: Any = None  # sparse matrix after fitting

    @property
    def is_empty(self) -> bool:
        return len(self._documents) == 0

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the store and rebuild the TF-IDF index.

        Args:
            documents: List of Document objects to add.
        """
        if not documents:
            return
        self._documents.extend(documents)
        self._rebuild_index()

    def clear(self) -> None:
        """Remove all documents and reset the index."""
        self._documents = []
        self._matrix = None
        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b\w+\b",
            sublinear_tf=True,
        )

    def search(self, query: str, k: int = 5) -> list[Document]:
        """Return the top-k most relevant documents for a query.

        Args:
            query: Natural language question or search string.
            k: Maximum number of documents to return.

        Returns:
            List of the most relevant Documents, sorted by relevance.
        """
        if self.is_empty or not query.strip():
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        top_indices = np.argsort(scores)[::-1][:k]
        return [self._documents[i] for i in top_indices if scores[i] > 0]

    def _rebuild_index(self) -> None:
        corpus = [doc.content for doc in self._documents]
        self._matrix = self._vectorizer.fit_transform(corpus)

    def __len__(self) -> int:
        return len(self._documents)
