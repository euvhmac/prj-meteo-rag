"""Retriever TF-IDF para busca semântica em chunks meteorológicos.

Usa scikit-learn ``TfidfVectorizer`` + similaridade cosseno para
ranquear chunks por relevância a uma query em linguagem natural.
O índice é reconstruído completamente ao indexar novos dados.
"""

from __future__ import annotations

import logging
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from meteorag.config import Settings

logger = logging.getLogger(__name__)


class TFIDFRetriever:
    """Retriever baseado em TF-IDF para chunks meteorológicos.

    O índice é reconstruído do zero ao adicionar novos chunks
    (não incremental, conforme ADR-001).

    Attributes:
        top_k: Número de chunks retornados por busca.

    Example:
        >>> retriever = TFIDFRetriever()
        >>> retriever.index(chunks)
        >>> results = retriever.search("chuva em Juiz de Fora")
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self.top_k = self._settings.rag_top_k
        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
        )
        self._tfidf_matrix: Any = None
        self._chunks: list[dict[str, Any]] = []
        self._is_indexed = False

    @property
    def is_indexed(self) -> bool:
        """Indica se há chunks indexados."""
        return self._is_indexed

    @property
    def chunk_count(self) -> int:
        """Número total de chunks no índice."""
        return len(self._chunks)

    def index(self, chunks: list[dict[str, Any]]) -> int:
        """Constrói (ou reconstrói) o índice TF-IDF a partir dos chunks.

        O índice anterior é completamente substituído.

        Args:
            chunks: Lista de chunks ``{"text": str, "metadata": dict}``.

        Returns:
            Número de chunks indexados.
        """
        if not chunks:
            logger.warning("Nenhum chunk fornecido para indexação.")
            self._chunks = []
            self._tfidf_matrix = None
            self._is_indexed = False
            return 0

        # Filtra chunks com texto válido
        valid_chunks = [c for c in chunks if c.get("text", "").strip()]
        if not valid_chunks:
            logger.warning("Todos os chunks fornecidos estão vazios.")
            self._chunks = []
            self._tfidf_matrix = None
            self._is_indexed = False
            return 0

        self._chunks = valid_chunks
        texts = [c["text"] for c in valid_chunks]

        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        self._is_indexed = True

        logger.info("Índice TF-IDF construído com %d chunks.", len(valid_chunks))
        return len(valid_chunks)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        filter_type: str | None = None,
        filter_city: str | None = None,
    ) -> list[dict[str, Any]]:
        """Busca os chunks mais relevantes para uma query.

        Args:
            query: Texto da busca em linguagem natural.
            top_k: Número de resultados (default: ``self.top_k``).
            filter_type: Filtro opcional por tipo de chunk
                (``daily``, ``hourly``, ``alert``, ``context``).
            filter_city: Filtro opcional por cidade.

        Returns:
            Lista de chunks com score > 0, ordenados por relevância
            decrescente. Cada chunk inclui ``score`` no dicionário.
            Retorna lista vazia se não houver índice ou nenhum match.
        """
        if not self._is_indexed or self._tfidf_matrix is None:
            logger.warning("Busca sem índice. Chame index() primeiro.")
            return []

        if not query.strip():
            logger.warning("Query vazia.")
            return []

        k = top_k or self.top_k

        # Vetoriza a query
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Filtra por metadata se necessário
        candidate_indices = list(range(len(self._chunks)))

        if filter_type is not None:
            candidate_indices = [
                i
                for i in candidate_indices
                if self._chunks[i].get("metadata", {}).get("type") == filter_type
            ]

        if filter_city is not None:
            filter_city_lower = filter_city.lower()
            candidate_indices = [
                i
                for i in candidate_indices
                if self._chunks[i].get("metadata", {}).get("city", "").lower() == filter_city_lower
            ]

        # Ordena por score (descendente) e filtra score > 0
        scored = [(i, scores[i]) for i in candidate_indices if scores[i] > 0]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored[:k]:
            chunk = dict(self._chunks[idx])
            chunk["score"] = round(float(score), 4)
            results.append(chunk)

        logger.info(
            "Busca '%s': %d resultados (de %d candidatos, top_k=%d)",
            query[:50],
            len(results),
            len(scored),
            k,
        )

        return results

    def get_all_chunks(self) -> list[dict[str, Any]]:
        """Retorna todos os chunks indexados (sem score).

        Returns:
            Cópia da lista interna de chunks.
        """
        return list(self._chunks)

    def clear(self) -> None:
        """Remove todos os chunks e o índice."""
        self._chunks = []
        self._tfidf_matrix = None
        self._is_indexed = False
        logger.info("Índice TF-IDF limpo.")
