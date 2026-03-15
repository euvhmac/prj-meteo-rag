"""Testes de integração para pipeline.py e fluxo RAG → LLM.

Marcados com @pytest.mark.integration — requerem .env configurado.
Executar com: pytest tests/integration/ -v -m integration
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from meteorag.llm.client import (
    FALLBACK_MESSAGE,
    SYSTEM_PROMPT,
    ask,
    build_messages,
    trim_history,
)
from meteorag.rag.pipeline import MeteoRAG


@pytest.mark.integration
class TestRAGPipelineIntegration:
    """Testes de integração do pipeline completo (com dados mockados).

    Simula o fluxo completo: dados Open-Meteo → chunks → índice → busca,
    sem requisições HTTP reais.
    """

    @pytest.fixture()
    def mock_rag(
        self,
        sample_openmeteo_response: dict[str, Any],
        sample_alerts: list[dict[str, Any]],
    ) -> MeteoRAG:
        """Cria MeteoRAG com clients mockados."""
        rag = MeteoRAG()

        # Mock do Open-Meteo HTTP
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_openmeteo_response
        mock_resp.text = "{}"
        mock_resp.raise_for_status = MagicMock()

        # Mock dos alertas INMET
        mock_alerts_resp = MagicMock()
        mock_alerts_resp.status_code = 200
        mock_alerts_resp.json.return_value = sample_alerts
        mock_alerts_resp.raise_for_status = MagicMock()

        with (
            patch.object(rag.weather_client._session, "get", return_value=mock_resp),
            patch.object(
                rag.inmet_client._session,
                "get",
                return_value=mock_alerts_resp,
            ),
        ):
            rag.index_city("Juiz de Fora")

        return rag

    def test_pipeline_indexes_and_retrieves(self, mock_rag: MeteoRAG) -> None:
        """Verifica que o pipeline indexa dados e retorna resultados."""
        assert mock_rag.is_ready
        assert mock_rag.total_chunks > 0

        results = mock_rag.retrieve("chuva em Juiz de Fora")
        assert len(results) > 0

    def test_pipeline_context_for_llm(self, mock_rag: MeteoRAG) -> None:
        """Verifica que get_context_for_llm retorna texto formatado."""
        context = mock_rag.get_context_for_llm("previsão de chuva")
        assert isinstance(context, str)
        assert len(context) > 0
        assert "Relevância" in context

    def test_pipeline_filter_by_type(self, mock_rag: MeteoRAG) -> None:
        """Verifica que filtros de tipo funcionam."""
        alerts = mock_rag.retrieve("alerta", filter_type="alert")
        for a in alerts:
            assert a["metadata"]["type"] == "alert"

    def test_pipeline_empty_before_index(self) -> None:
        """Verifica que busca sem indexação retorna vazio."""
        rag = MeteoRAG()
        assert rag.is_ready is False
        results = rag.retrieve("qualquer coisa")
        assert results == []

    def test_pipeline_context_when_no_data(self) -> None:
        """Verifica mensagem de fallback quando não há dados."""
        rag = MeteoRAG()
        context = rag.get_context_for_llm("chuva")
        assert "indisponíveis" in context.lower() or "indisponível" in context.lower()

    def test_indexed_cities_tracked(self, mock_rag: MeteoRAG) -> None:
        """Verifica que cidades indexadas são rastreadas."""
        assert "Juiz de Fora" in mock_rag.indexed_cities


# ══════════════════════════════════════════════════════════
# Testes de integração RAG → LLM (S5-01)
# ══════════════════════════════════════════════════════════


@pytest.mark.integration
class TestRAGToLLMIntegration:
    """Testes end-to-end do fluxo RAG → LLM.

    Usa pipeline RAG real (com dados mockados) + LLM mockado
    para verificar que contexto, mensagens e resposta fluem corretamente.
    """

    @pytest.fixture()
    def indexed_rag(
        self,
        sample_openmeteo_response: dict[str, Any],
        sample_alerts: list[dict[str, Any]],
    ) -> MeteoRAG:
        """Cria MeteoRAG indexado com dados de teste."""
        rag = MeteoRAG()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_openmeteo_response
        mock_resp.text = "{}"
        mock_resp.raise_for_status = MagicMock()

        mock_alerts_resp = MagicMock()
        mock_alerts_resp.status_code = 200
        mock_alerts_resp.json.return_value = sample_alerts
        mock_alerts_resp.raise_for_status = MagicMock()

        with (
            patch.object(rag.weather_client._session, "get", return_value=mock_resp),
            patch.object(rag.inmet_client._session, "get", return_value=mock_alerts_resp),
        ):
            rag.index_city("Juiz de Fora")

        return rag

    def test_rag_context_flows_to_llm_messages(self, indexed_rag: MeteoRAG) -> None:
        """Verifica que contexto RAG é corretamente injetado nas mensagens do LLM."""
        query = "Choveu em Juiz de Fora ontem?"
        context = indexed_rag.get_context_for_llm(query)

        messages = build_messages(query, context)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "[CONTEXTO METEOROLÓGICO RECUPERADO]" in messages[0]["content"]
        assert "[PERGUNTA DO USUÁRIO]" in messages[0]["content"]
        assert "Juiz de Fora" in messages[0]["content"]
        assert "Relevância" in messages[0]["content"]

    def test_rag_context_with_history(self, indexed_rag: MeteoRAG) -> None:
        """Verifica que histórico de chat é preservado junto com contexto RAG."""
        history = [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Olá! Como posso ajudar?"},
        ]
        query = "Qual a temperatura máxima?"
        context = indexed_rag.get_context_for_llm(query)

        messages = build_messages(query, context, history)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Olá"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert "[CONTEXTO METEOROLÓGICO RECUPERADO]" in messages[2]["content"]

    def test_llm_ask_receives_rag_context(self, indexed_rag: MeteoRAG) -> None:
        """Verifica que ask() envia contexto RAG ao LLM e retorna resposta."""
        query = "Tem alerta de chuva forte?"
        context = indexed_rag.get_context_for_llm(query)

        # Mock do cliente Anthropic
        mock_content = MagicMock()
        mock_content.text = "Sim, há um alerta de chuvas intensas para Juiz de Fora."

        mock_response = MagicMock()
        mock_response.content = [mock_content]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = ask(query, context, client=mock_client)

        assert "alerta" in result.lower()
        # Verifica que o LLM foi chamado com system prompt e contexto
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["system"] == SYSTEM_PROMPT
        sent_messages = call_kwargs.kwargs["messages"]
        assert "[CONTEXTO METEOROLÓGICO RECUPERADO]" in sent_messages[-1]["content"]

    def test_llm_fallback_on_error(self, indexed_rag: MeteoRAG) -> None:
        """Verifica que erro do LLM retorna mensagem de fallback (não crash)."""
        query = "Previsão para amanhã?"
        context = indexed_rag.get_context_for_llm(query)

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("LLM indisponível")

        result = ask(query, context, client=mock_client)
        assert result == FALLBACK_MESSAGE

    def test_llm_receives_trimmed_history(self, indexed_rag: MeteoRAG) -> None:
        """Verifica que histórico longo é trimado antes de enviar ao LLM."""
        # Cria histórico com 20 mensagens (excede MAX_HISTORY_MESSAGES=10)
        history: list[dict[str, str]] = []
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            history.append({"role": role, "content": f"Msg {i}"})

        trimmed = trim_history(history)
        assert len(trimmed) <= 10
        # Deve começar com user
        assert trimmed[0]["role"] == "user"

    def test_full_flow_query_to_response(self, indexed_rag: MeteoRAG) -> None:
        """Teste end-to-end: query → RAG retrieve → build context → LLM → response."""
        query = "Quanto choveu esta semana em Juiz de Fora?"

        # Step 1: RAG retrieval
        results = indexed_rag.retrieve(query)
        assert len(results) > 0

        # Step 2: Build context
        context = indexed_rag.get_context_for_llm(query)
        assert "Relevância" in context
        assert len(context) > 50

        # Step 3: Build messages
        messages = build_messages(query, context)
        assert len(messages) == 1

        # Step 4: Mock LLM call
        mock_content = MagicMock()
        mock_content.text = (
            "Com base nos dados do Open-Meteo, choveu 18.0mm em " "Juiz de Fora no dia 15/01/2024."
        )
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        # Step 5: Get response
        response = ask(query, context, client=mock_client)
        assert "18.0mm" in response or "chuv" in response.lower()
        mock_client.messages.create.assert_called_once()

    def test_alert_context_included_in_llm(self, indexed_rag: MeteoRAG) -> None:
        """Verifica que alertas INMET sao indexados e recuperaveis via RAG."""
        # Verifica que chunks de alerta foram indexados
        all_chunks = indexed_rag.retriever.get_all_chunks()
        alert_chunks = [c for c in all_chunks if c.get("metadata", {}).get("type") == "alert"]
        assert len(alert_chunks) > 0, "Nenhum chunk de alerta foi indexado"

        # Verifica que texto do alerta contem informacoes esperadas
        alert_text = alert_chunks[0]["text"]
        assert "ALERTA" in alert_text.upper()

        # Busca com filtro de tipo retorna alertas
        results = indexed_rag.retrieve("chuva perigo", filter_type="alert")
        assert len(results) > 0, "Busca filtrada por tipo=alert nao retornou resultados"
        assert "ALERTA" in results[0]["text"].upper()

    def test_empty_context_handled_gracefully(self) -> None:
        """Verifica que LLM funciona mesmo com contexto de 'dados indisponíveis'."""
        rag = MeteoRAG()
        context = rag.get_context_for_llm("qualquer pergunta")

        mock_content = MagicMock()
        mock_content.text = "Não tenho dados disponíveis no momento."
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        result = ask("qualquer pergunta", context, client=mock_client)
        assert "dados" in result.lower() or "disponív" in result.lower()
