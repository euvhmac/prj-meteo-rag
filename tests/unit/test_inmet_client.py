"""Testes unitários para inmet_client.py.

Todos os testes usam fixtures locais — sem requisições HTTP reais.
"""

from __future__ import annotations

from typing import Any


class TestSampleFixtures:
    """Testes de sanidade para verificar que as fixtures estão funcionando."""

    def test_stations_fixture_has_data(self, sample_stations: list[dict[str, Any]]) -> None:
        """Verifica que a fixture de estações contém dados."""
        assert len(sample_stations) > 0

    def test_stations_have_required_fields(self, sample_stations: list[dict[str, Any]]) -> None:
        """Verifica campos obrigatórios nas estações."""
        required_fields = {"CD_ESTACAO", "DC_NOME", "SG_ESTADO"}
        for station in sample_stations:
            assert required_fields.issubset(station.keys())

    def test_mg_stations_present(self, sample_stations: list[dict[str, Any]]) -> None:
        """Verifica que há estações de MG nos dados."""
        mg_stations = [s for s in sample_stations if s["SG_ESTADO"] == "MG"]
        assert len(mg_stations) >= 3

    def test_observations_have_required_fields(
        self, sample_hourly_observations: list[dict[str, Any]]
    ) -> None:
        """Verifica campos obrigatórios nas observações."""
        required_fields = {"CD_ESTACAO", "DT_MEDICAO", "HR_MEDICAO", "CHUVA", "TEM_INS"}
        for obs in sample_hourly_observations:
            assert required_fields.issubset(obs.keys())

    def test_observations_with_nulls_have_invalid_values(
        self, sample_observations_with_nulls: list[dict[str, Any]]
    ) -> None:
        """Verifica que fixture de dados nulos contém valores inválidos."""
        obs = sample_observations_with_nulls[0]
        # Pelo menos um campo deve ser None, -9999 ou vazio
        has_invalid = any(
            v is None or v == "" or v in ("-9999", "9999")
            for v in [obs["CHUVA"], obs["TEM_INS"], obs["TEM_MAX"], obs["TEM_MIN"]]
        )
        assert has_invalid

    def test_alerts_have_required_fields(self, sample_alerts: list[dict[str, Any]]) -> None:
        """Verifica campos obrigatórios nos alertas."""
        required_fields = {"descricao", "severidade", "evento", "municipios"}
        for alert in sample_alerts:
            assert required_fields.issubset(alert.keys())

    def test_empty_alerts_is_empty(self, empty_alerts: list[dict[str, Any]]) -> None:
        """Verifica que a fixture de alertas vazios é uma lista vazia."""
        assert empty_alerts == []
