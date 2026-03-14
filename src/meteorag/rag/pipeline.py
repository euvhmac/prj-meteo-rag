"""Pipeline RAG — orquestra Open-Meteo client, INMET alerts, chunker e retriever.

Classe ``MeteoRAG`` é o ponto de entrada principal que coordena:
1. Busca de dados meteorológicos via ``OpenMeteoClient`` (fonte principal)
2. Busca de alertas via ``INMETClient`` (best-effort)
3. Conversão em chunks via ``MeteoChunker``
4. Indexação e busca via ``TFIDFRetriever``
"""

from __future__ import annotations

import logging
from typing import Any

from meteorag.api.inmet_client import INMETClient
from meteorag.api.openmeteo_client import MG_CITIES, OpenMeteoClient
from meteorag.config import Settings
from meteorag.rag.chunker import MeteoChunker
from meteorag.rag.retriever import TFIDFRetriever

logger = logging.getLogger(__name__)


class MeteoRAG:
    """Pipeline RAG meteorológico completo.

    Coordena a busca de dados do Open-Meteo (principal) e alertas
    do INMET, chunking e retrieval TF-IDF para responder perguntas
    sobre clima em Minas Gerais.

    Attributes:
        weather_client: Cliente da API Open-Meteo (fonte principal).
        inmet_client: Cliente da API INMET (apenas alertas).
        chunker: Conversor de dados para chunks textuais.
        retriever: Motor de busca TF-IDF.

    Example:
        >>> rag = MeteoRAG()
        >>> rag.index_city("Juiz de Fora")
        >>> results = rag.retrieve("chuva ontem")
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self.weather_client = OpenMeteoClient(self._settings)
        self.inmet_client = INMETClient(self._settings)
        self.chunker = MeteoChunker(self._settings)
        self.retriever = TFIDFRetriever(self._settings)
        self._all_chunks: list[dict[str, Any]] = []
        self._indexed_cities: set[str] = set()

    @property
    def is_ready(self) -> bool:
        """Indica se o pipeline tem dados indexados e está pronto para buscas."""
        return self.retriever.is_indexed

    @property
    def indexed_cities(self) -> set[str]:
        """Conjunto de cidades já indexadas."""
        return set(self._indexed_cities)

    @property
    def total_chunks(self) -> int:
        """Total de chunks no índice."""
        return self.retriever.chunk_count

    def index_city(
        self,
        city: str,
        days_back: int | None = None,
    ) -> int:
        """Busca dados do Open-Meteo + alertas INMET e indexa os chunks.

        O índice TF-IDF é reconstruído do zero incluindo todos os
        chunks acumulados (de todas as cidades já indexadas).

        Args:
            city: Nome da cidade (deve existir em ``MG_CITIES``).
            days_back: Dias retroativos (default: ``default_days_back``).

        Returns:
            Número total de chunks no índice após indexação.
        """
        if days_back is None:
            days_back = self._settings.default_days_back

        logger.info("Indexando %s (days_back=%d)", city, days_back)

        # Busca dados via Open-Meteo (fonte principal)
        observations = self.weather_client.get_observations(city, days_back)
        daily_summaries = self.weather_client.get_daily_summaries(city, days_back)

        # Alertas INMET (best-effort — não falha se indisponível)
        alerts = self._fetch_alerts_safe()

        # Gera chunks
        new_chunks = self.chunker.chunk_all(
            daily_summaries=daily_summaries,
            observations=observations,
            alerts=alerts,
            city=city,
            station_code="Open-Meteo",
        )

        if not new_chunks:
            logger.warning("Nenhum chunk gerado para %s.", city)
            return self.retriever.chunk_count

        # Remove chunks antigos da mesma cidade e acumula novos
        self._all_chunks = [
            c for c in self._all_chunks if c.get("metadata", {}).get("city") != city
        ]
        self._all_chunks.extend(new_chunks)
        self._indexed_cities.add(city)

        # Reconstrói índice TF-IDF com todos os chunks
        total = self.retriever.index(self._all_chunks)

        logger.info(
            "Indexação completa: %d novos chunks para %s. Total no índice: %d",
            len(new_chunks),
            city,
            total,
        )

        return total

    def index_priority_cities(
        self,
        days_back: int | None = None,
    ) -> int:
        """Indexa todas as cidades prioritárias de MG.

        Args:
            days_back: Dias retroativos.

        Returns:
            Número total de chunks no índice.
        """
        for city in MG_CITIES:
            self.index_city(city, days_back)

        return self.retriever.chunk_count

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_type: str | None = None,
        filter_city: str | None = None,
    ) -> list[dict[str, Any]]:
        """Busca chunks relevantes para uma query.

        Args:
            query: Pergunta em linguagem natural.
            top_k: Número máximo de resultados.
            filter_type: Filtro por tipo de chunk.
            filter_city: Filtro por cidade.

        Returns:
            Lista de chunks com score, ordenados por relevância.
        """
        if not self.is_ready:
            logger.warning("Pipeline não indexado. Chame index_city() primeiro.")
            return []

        return self.retriever.search(
            query=query,
            top_k=top_k,
            filter_type=filter_type,
            filter_city=filter_city,
        )

    def get_context_for_llm(
        self,
        query: str,
        top_k: int | None = None,
    ) -> str:
        """Retorna contexto formatado para envio ao LLM.

        Concatena os chunks mais relevantes em um único texto,
        separados por linha dupla.

        Args:
            query: Pergunta do usuário.
            top_k: Número de chunks a incluir.

        Returns:
            Texto de contexto formatado ou mensagem de dados indisponíveis.
        """
        results = self.retrieve(query, top_k=top_k)

        if not results:
            return (
                "Não há dados meteorológicos disponíveis no momento. "
                "Os dados podem estar sendo atualizados ou a API "
                "pode estar temporariamente indisponível."
            )

        context_parts = []
        for chunk in results:
            score = chunk.get("score", 0)
            text = chunk.get("text", "")
            context_parts.append(f"[Relevância: {score:.2f}] {text}")

        return "\n\n".join(context_parts)

    def refresh(self) -> int:
        """Re-indexa todas as cidades previamente indexadas com dados frescos.

        Limpa os caches e reconstrói o índice.

        Returns:
            Número total de chunks após re-indexação.
        """
        self.weather_client.clear_cache()

        cities_to_reindex = set(self._indexed_cities)
        if not cities_to_reindex:
            logger.info("Nenhuma cidade para re-indexar.")
            return self.retriever.chunk_count

        self._all_chunks = []
        self._indexed_cities.clear()

        for city in cities_to_reindex:
            self.index_city(city)

        return self.retriever.chunk_count

    def _fetch_alerts_safe(self) -> list[dict[str, Any]]:
        """Busca alertas INMET de forma segura (best-effort).

        Nunca propaga exceções — retorna lista vazia se falhar.

        Returns:
            Lista de alertas ou ``[]``.
        """
        try:
            return self.inmet_client.get_alerts("MG")
        except Exception as exc:
            logger.warning("Falha ao buscar alertas INMET (best-effort): %s", exc)
            return []
