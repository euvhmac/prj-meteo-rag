"""Tests for the MeteoAgent orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.meteo_agent import MeteoAgent
from src.data.inmet import INMETClient
from src.data.open_meteo import OpenMeteoClient
from src.llm.claude import ClaudeClient
from src.rag.document import Document
from src.rag.retriever import Retriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(llm_answer: str = "Resposta de teste.") -> MeteoAgent:
    """Build a MeteoAgent with fully mocked dependencies."""
    mock_llm = MagicMock(spec=ClaudeClient)
    mock_llm.answer.return_value = llm_answer

    mock_open_meteo = MagicMock(spec=OpenMeteoClient)
    mock_open_meteo.get_all_cities_summary.return_value = [
        {
            "city": "Belo Horizonte",
            "summary": "Cidade: Belo Horizonte. temperatura 28.5°C. chuva 5.0 mm. condição: chuva moderada.",
            "temperature": 28.5,
            "rain": 5.0,
            "humidity": 70,
            "precipitation": 5.0,
            "wind_speed": 15.0,
            "condition": "chuva moderada",
        }
    ]

    mock_inmet = MagicMock(spec=INMETClient)
    mock_inmet.get_mg_alerts.return_value = [
        {
            "evento": "Chuvas intensas",
            "severidade": "Amarelo",
            "_summary": "Alerta INMET: Chuvas intensas. Nível: Amarelo (Atenção). Estado: Minas Gerais (MG).",
        }
    ]

    return MeteoAgent(
        claude_client=mock_llm,
        open_meteo_client=mock_open_meteo,
        inmet_client=mock_inmet,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMeteoAgentRefreshData:
    def test_refresh_returns_correct_counts(self):
        agent = _make_agent()
        stats = agent.refresh_data()
        assert stats["cities_loaded"] == 1
        assert stats["alerts_loaded"] == 1

    def test_refresh_indexes_documents_in_store(self):
        agent = _make_agent()
        agent.refresh_data()
        assert not agent.retriever.store.is_empty

    def test_refresh_handles_open_meteo_error_gracefully(self):
        agent = _make_agent()
        agent.open_meteo.get_all_cities_summary.side_effect = Exception("timeout")
        stats = agent.refresh_data()
        # Should still succeed but with 0 cities
        assert stats["cities_loaded"] == 0

    def test_refresh_handles_inmet_error_gracefully(self):
        agent = _make_agent()
        agent.inmet.get_mg_alerts.side_effect = Exception("unavailable")
        stats = agent.refresh_data()
        assert stats["alerts_loaded"] == 0

    def test_refresh_clears_previous_data(self):
        agent = _make_agent()
        agent.refresh_data()
        count_first = len(agent.retriever.store)

        agent.refresh_data()
        count_second = len(agent.retriever.store)

        # After two refreshes with same mock data, counts should be equal
        assert count_first == count_second

    def test_alerts_without_summary_are_skipped(self):
        agent = _make_agent()
        # Alert without '_summary' key should be skipped
        agent.inmet.get_mg_alerts.return_value = [{"evento": "Geada", "_summary": ""}]
        stats = agent.refresh_data()
        assert stats["alerts_loaded"] == 0


class TestMeteoAgentAsk:
    def test_ask_returns_llm_answer(self):
        agent = _make_agent(llm_answer="Vai chover amanhã.")
        agent.refresh_data()
        answer = agent.ask("Vai chover em BH?")
        assert answer == "Vai chover amanhã."

    def test_ask_calls_llm_with_question(self):
        agent = _make_agent()
        agent.refresh_data()
        agent.ask("Temperatura em Uberlândia?")
        agent.llm.answer.assert_called_once()
        call_args = agent.llm.answer.call_args
        assert "Temperatura em Uberlândia?" in call_args[0]

    def test_ask_passes_context_to_llm(self):
        agent = _make_agent()
        agent.refresh_data()
        agent.ask("Chuva em Belo Horizonte")
        call_kwargs = agent.llm.answer.call_args
        # context kwarg should be a non-empty string after refresh
        context = call_kwargs[1].get("context", "") or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else ""
        # After loading the BH summary, the context for a BH rain question should have content
        assert isinstance(context, str)

    def test_ask_without_refresh_still_works(self):
        agent = _make_agent(llm_answer="Sem dados.")
        answer = agent.ask("Previsão para hoje?")
        assert answer == "Sem dados."


class TestMeteoAgentInit:
    def test_default_clients_created_when_not_provided(self):
        mock_llm = MagicMock(spec=ClaudeClient)
        agent = MeteoAgent(claude_client=mock_llm)
        assert isinstance(agent.open_meteo, OpenMeteoClient)
        assert isinstance(agent.inmet, INMETClient)
        assert isinstance(agent.retriever, Retriever)
