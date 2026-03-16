"""Main MeteoAgent that orchestrates data fetching, RAG, and LLM answering."""

from __future__ import annotations

import logging
from typing import Any

from src.data.inmet import INMETClient
from src.data.open_meteo import OpenMeteoClient
from src.llm.claude import ClaudeClient
from src.rag.document import Document
from src.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class MeteoAgent:
    """Intelligent meteorological agent for Minas Gerais.

    Combines real-time weather data from Open-Meteo and INMET alerts
    with a RAG pipeline (TF-IDF retrieval) and Claude Haiku to answer
    natural language questions about weather conditions.

    Args:
        claude_client: Pre-built ClaudeClient instance.
        open_meteo_client: Pre-built OpenMeteoClient instance.
        inmet_client: Pre-built INMETClient instance.
        retriever: Pre-built Retriever instance.
    """

    def __init__(
        self,
        claude_client: ClaudeClient,
        open_meteo_client: OpenMeteoClient | None = None,
        inmet_client: INMETClient | None = None,
        retriever: Retriever | None = None,
    ) -> None:
        self.llm = claude_client
        self.open_meteo = open_meteo_client or OpenMeteoClient()
        self.inmet = inmet_client or INMETClient()
        self.retriever = retriever or Retriever()

    def refresh_data(self) -> dict[str, Any]:
        """Fetch fresh weather data and alerts, index them in the RAG store.

        Returns:
            Summary dict with counts of loaded cities and alerts.
        """
        self.retriever.store.clear()
        documents: list[Document] = []

        # 1. Fetch weather summaries for MG cities
        city_count = 0
        try:
            summaries = self.open_meteo.get_all_cities_summary()
            for s in summaries:
                doc = Document(
                    content=s["summary"],
                    metadata={
                        "source": "open-meteo",
                        "city": s["city"],
                        "type": "weather_summary",
                    },
                )
                documents.append(doc)
                city_count += 1
            logger.info("Carregados dados de %d cidades.", city_count)
        except Exception as exc:
            logger.warning("Erro ao buscar dados Open-Meteo: %s", exc)

        # 2. Fetch INMET alerts for MG
        alert_count = 0
        try:
            alerts = self.inmet.get_mg_alerts()
            for alert in alerts:
                summary = alert.get("_summary", "")
                if summary:
                    doc = Document(
                        content=summary,
                        metadata={
                            "source": "inmet",
                            "type": "alert",
                            "severity": alert.get("severidade")
                            or alert.get("severity", ""),
                        },
                    )
                    documents.append(doc)
                    alert_count += 1
            logger.info("Carregados %d alertas INMET para MG.", alert_count)
        except Exception as exc:
            logger.warning("Erro ao buscar alertas INMET: %s", exc)

        if documents:
            self.retriever.add_documents(documents)

        return {"cities_loaded": city_count, "alerts_loaded": alert_count}

    def ask(self, question: str, k: int = 5) -> str:
        """Answer a natural language meteorological question.

        Retrieves relevant context from the RAG store and passes it
        together with the question to Claude Haiku.

        Args:
            question: User question in natural language.
            k: Number of RAG context passages to retrieve.

        Returns:
            Natural language answer from Claude Haiku.
        """
        context = self.retriever.retrieve_context(question, k=k)
        logger.debug(
            "Contexto recuperado (%d chars) para: %s", len(context), question
        )
        return self.llm.answer(question, context=context)
