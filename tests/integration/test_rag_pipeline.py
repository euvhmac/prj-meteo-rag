"""Testes de integração para pipeline.py.

Marcados com @pytest.mark.integration — requerem .env configurado.
Executar com: pytest tests/integration/ -v -m integration
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from meteorag.rag.pipeline import MeteoRAG


@pytest.mark.integration
class TestRAGPipelineIntegration:
    """Testes de integração do pipeline completo (com dados mockados).

    Simula o fluxo completo: dados INMET → chunks → índice → busca,
    sem requisições HTTP reais.
    """

    @pytest.fixture()
    def mock_rag(
        self,
        sample_hourly_observations: list[dict[str, Any]],
        sample_alerts: list[dict[str, Any]],
    ) -> MeteoRAG:
        """Cria MeteoRAG com client INMET mockado."""
        rag = MeteoRAG()

        # Mock das chamadas HTTP
        mock_resp_obs = MagicMock()
        mock_resp_obs.status_code = 200
        mock_resp_obs.json.return_value = sample_hourly_observations
        mock_resp_obs.raise_for_status = MagicMock()

        mock_resp_alerts = MagicMock()
        mock_resp_alerts.status_code = 200
        mock_resp_alerts.json.return_value = sample_alerts
        mock_resp_alerts.raise_for_status = MagicMock()

        def side_effect(url: str, **kwargs: Any) -> MagicMock:
            if "alertas" in url:
                return mock_resp_alerts
            return mock_resp_obs

        with patch.object(rag.client._session, "get", side_effect=side_effect):
            rag.index_city("A518", "Juiz de Fora")

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
