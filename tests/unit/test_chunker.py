"""Testes unitários para chunker.py.

Valida a conversão de dados meteorológicos em chunks de texto.
"""

from __future__ import annotations

from typing import Any

from meteorag.api.inmet_client import parse_observation
from meteorag.rag.chunker import (
    MeteoChunker,
    _fmt_date_br,
    _fmt_rain,
    _safe_fmt,
    chunk_alert,
    chunk_daily_summary,
    chunk_hourly_observation,
    chunk_weekly_context,
)

# ══════════════════════════════════════════════════════════
# _fmt_rain
# ══════════════════════════════════════════════════════════


class TestFmtRain:
    """Testes para classificação textual de chuva."""

    def test_none_rain(self) -> None:
        assert _fmt_rain(None) == "Sem dados de chuva"

    def test_zero_rain(self) -> None:
        assert _fmt_rain(0.0) == "Sem chuva registrada"

    def test_light_rain(self) -> None:
        result = _fmt_rain(3.0)
        assert "fraca" in result
        assert "3.0mm" in result

    def test_moderate_rain(self) -> None:
        result = _fmt_rain(15.0)
        assert "moderada" in result

    def test_heavy_rain(self) -> None:
        result = _fmt_rain(30.0)
        assert "forte" in result.lower()

    def test_very_heavy_rain(self) -> None:
        result = _fmt_rain(60.0)
        assert "muito forte" in result


# ══════════════════════════════════════════════════════════
# _fmt_date_br
# ══════════════════════════════════════════════════════════


class TestFmtDateBr:
    """Testes para formatação de data."""

    def test_valid_date(self) -> None:
        assert _fmt_date_br("2024-01-15") == "15/01/2024"

    def test_invalid_date_returns_original(self) -> None:
        assert _fmt_date_br("invalid") == "invalid"

    def test_empty_string(self) -> None:
        assert _fmt_date_br("") == ""


# ══════════════════════════════════════════════════════════
# _safe_fmt
# ══════════════════════════════════════════════════════════


class TestSafeFmt:
    """Testes para formatação segura de valores."""

    def test_valid_value(self) -> None:
        assert _safe_fmt(22.5, "°C") == "22.5°C"

    def test_none_value(self) -> None:
        assert _safe_fmt(None, "°C") == "sem dados"

    def test_custom_decimals(self) -> None:
        assert _safe_fmt(78.0, "%", decimals=0) == "78%"


# ══════════════════════════════════════════════════════════
# chunk_daily_summary
# ══════════════════════════════════════════════════════════


class TestChunkDailySummary:
    """Testes para geração de chunks diários."""

    def test_generates_valid_chunk(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        chunk = chunk_daily_summary(sample_daily_summaries[0])

        assert "text" in chunk
        assert "metadata" in chunk
        assert chunk["metadata"]["type"] == "daily"
        assert chunk["metadata"]["city"] == "Juiz de Fora"
        assert chunk["metadata"]["date"] == "2024-01-15"

    def test_text_contains_city(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        chunk = chunk_daily_summary(sample_daily_summaries[0])
        assert "Juiz de Fora" in chunk["text"]

    def test_text_contains_rain_info(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        chunk = chunk_daily_summary(sample_daily_summaries[0])
        assert "18.0mm" in chunk["text"]

    def test_no_rain_day(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        chunk = chunk_daily_summary(sample_daily_summaries[1])
        assert "Sem chuva" in chunk["text"]

    def test_text_within_max_size(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        for summary in sample_daily_summaries:
            chunk = chunk_daily_summary(summary)
            assert len(chunk["text"]) <= 512

    def test_handles_none_values(self) -> None:
        summary = {
            "city": "Test",
            "station_code": "T001",
            "date": "2024-01-01",
            "total_rain_mm": None,
            "max_temp_c": None,
            "min_temp_c": None,
            "avg_humidity_pct": None,
            "observation_count": 0,
        }
        chunk = chunk_daily_summary(summary)
        assert "sem dados" in chunk["text"].lower() or "Sem dados" in chunk["text"]

    def test_single_observation_text(self) -> None:
        summary = {
            "city": "Barbacena",
            "station_code": "A519",
            "date": "2024-01-20",
            "total_rain_mm": 5.0,
            "max_temp_c": 20.0,
            "min_temp_c": 15.0,
            "avg_humidity_pct": 70.0,
            "observation_count": 1,
        }
        chunk = chunk_daily_summary(summary)
        assert "observação" in chunk["text"]  # singular


# ══════════════════════════════════════════════════════════
# chunk_hourly_observation
# ══════════════════════════════════════════════════════════


class TestChunkHourlyObservation:
    """Testes para geração de chunks horários."""

    def test_generates_valid_chunk(self, sample_hourly_observations: list[dict[str, Any]]) -> None:
        obs = parse_observation(sample_hourly_observations[2])  # 15.6mm de chuva
        chunk = chunk_hourly_observation(obs, "Juiz de Fora")

        assert chunk["metadata"]["type"] == "hourly"
        assert chunk["metadata"]["city"] == "Juiz de Fora"
        assert "15.6mm" in chunk["text"]

    def test_no_rain_observation(self, sample_hourly_observations: list[dict[str, Any]]) -> None:
        obs = parse_observation(sample_hourly_observations[1])  # CHUVA: 0.0
        chunk = chunk_hourly_observation(obs, "Juiz de Fora")
        assert "Sem chuva" in chunk["text"]

    def test_includes_wind(self, sample_hourly_observations: list[dict[str, Any]]) -> None:
        obs = parse_observation(sample_hourly_observations[0])
        chunk = chunk_hourly_observation(obs, "Juiz de Fora")
        assert "Vento" in chunk["text"]

    def test_within_max_size(self, sample_hourly_observations: list[dict[str, Any]]) -> None:
        for raw in sample_hourly_observations:
            obs = parse_observation(raw)
            chunk = chunk_hourly_observation(obs, "Juiz de Fora")
            assert len(chunk["text"]) <= 512


# ══════════════════════════════════════════════════════════
# chunk_alert
# ══════════════════════════════════════════════════════════


class TestChunkAlert:
    """Testes para geração de chunks de alerta."""

    def test_generates_valid_chunk(self, sample_alerts: list[dict[str, Any]]) -> None:
        chunk = chunk_alert(sample_alerts[0])

        assert chunk["metadata"]["type"] == "alert"
        assert "ALERTA METEOROLÓGICO" in chunk["text"]
        assert "Perigo" in chunk["text"]

    def test_contains_event(self, sample_alerts: list[dict[str, Any]]) -> None:
        chunk = chunk_alert(sample_alerts[0])
        assert "Chuvas Intensas" in chunk["text"]

    def test_contains_cities(self, sample_alerts: list[dict[str, Any]]) -> None:
        chunk = chunk_alert(sample_alerts[0])
        assert "Juiz de Fora" in chunk["text"]

    def test_within_max_size(self, sample_alerts: list[dict[str, Any]]) -> None:
        for alert in sample_alerts:
            chunk = chunk_alert(alert)
            assert len(chunk["text"]) <= 512

    def test_normalized_alert_format(self) -> None:
        normalized = {
            "state": "MG",
            "severity": "Perigo",
            "event": "Vendaval",
            "description": "Ventos de 80km/h",
            "cities": "Ubá",
            "start": "2024-02-01T12:00:00",
            "end": "2024-02-02T12:00:00",
        }
        chunk = chunk_alert(normalized)
        assert "Vendaval" in chunk["text"]
        assert "MG" in chunk["text"]


# ══════════════════════════════════════════════════════════
# chunk_weekly_context
# ══════════════════════════════════════════════════════════


class TestChunkWeeklyContext:
    """Testes para geração de chunks de contexto semanal."""

    def test_generates_valid_context(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        chunk = chunk_weekly_context(sample_daily_summaries, "Juiz de Fora", "A518")

        assert chunk is not None
        assert chunk["metadata"]["type"] == "context"
        assert "Contexto semanal" in chunk["text"]

    def test_contains_rain_stats(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        chunk = chunk_weekly_context(sample_daily_summaries, "Juiz de Fora", "A518")
        assert chunk is not None
        assert "18.0mm" in chunk["text"]
        assert "Dias com chuva" in chunk["text"]

    def test_empty_summaries_returns_none(self) -> None:
        result = chunk_weekly_context([], "Test", "T001")
        assert result is None

    def test_within_max_size(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        chunk = chunk_weekly_context(sample_daily_summaries, "Juiz de Fora", "A518")
        assert chunk is not None
        assert len(chunk["text"]) <= 512


# ══════════════════════════════════════════════════════════
# MeteoChunker
# ══════════════════════════════════════════════════════════


class TestMeteoChunker:
    """Testes para a classe orquestradora MeteoChunker."""

    def test_chunk_all_produces_chunks(
        self,
        sample_daily_summaries: list[dict[str, Any]],
        sample_hourly_observations: list[dict[str, Any]],
        sample_alerts: list[dict[str, Any]],
    ) -> None:
        observations = [parse_observation(o) for o in sample_hourly_observations]
        chunker = MeteoChunker()
        chunks = chunker.chunk_all(
            daily_summaries=sample_daily_summaries,
            observations=observations,
            alerts=sample_alerts,
            city="Juiz de Fora",
            station_code="A518",
        )

        assert len(chunks) > 0
        types = {c["metadata"]["type"] for c in chunks}
        assert "daily" in types
        assert "alert" in types
        assert "context" in types

    def test_chunk_all_respects_max_size(
        self,
        sample_daily_summaries: list[dict[str, Any]],
        sample_hourly_observations: list[dict[str, Any]],
        sample_alerts: list[dict[str, Any]],
    ) -> None:
        observations = [parse_observation(o) for o in sample_hourly_observations]
        chunker = MeteoChunker()
        chunks = chunker.chunk_all(
            daily_summaries=sample_daily_summaries,
            observations=observations,
            alerts=sample_alerts,
            city="Juiz de Fora",
            station_code="A518",
        )

        for chunk in chunks:
            assert len(chunk["text"]) <= 512

    def test_chunk_all_empty_inputs(self) -> None:
        chunker = MeteoChunker()
        chunks = chunker.chunk_all(
            daily_summaries=[],
            observations=[],
            alerts=[],
            city="Test",
            station_code="T001",
        )
        assert chunks == []

    def test_hourly_filter_only_rain(
        self,
        sample_daily_summaries: list[dict[str, Any]],
        sample_hourly_observations: list[dict[str, Any]],
    ) -> None:
        observations = [parse_observation(o) for o in sample_hourly_observations]
        chunker = MeteoChunker()
        chunks = chunker.chunk_all(
            daily_summaries=sample_daily_summaries,
            observations=observations,
            alerts=[],
            city="Juiz de Fora",
            station_code="A518",
        )

        hourly = [c for c in chunks if c["metadata"]["type"] == "hourly"]
        # Somente obs com chuva > 0: 2.4mm e 15.6mm
        assert len(hourly) == 2


# ══════════════════════════════════════════════════════════
# Fixture sanity checks (preservados)
# ══════════════════════════════════════════════════════════


class TestChunkFixtures:
    """Testes de sanidade para as fixtures de chunks."""

    def test_chunks_fixture_has_data(self, sample_chunks: list[dict[str, Any]]) -> None:
        assert len(sample_chunks) > 0

    def test_chunks_have_text_and_metadata(self, sample_chunks: list[dict[str, Any]]) -> None:
        for chunk in sample_chunks:
            assert "text" in chunk
            assert "metadata" in chunk
            assert isinstance(chunk["text"], str)
            assert len(chunk["text"]) > 0

    def test_chunks_metadata_has_required_fields(self, sample_chunks: list[dict[str, Any]]) -> None:
        for chunk in sample_chunks:
            meta = chunk["metadata"]
            assert "city" in meta
            assert "date" in meta
            assert "type" in meta

    def test_chunk_types_are_valid(self, sample_chunks: list[dict[str, Any]]) -> None:
        valid_types = {"hourly", "daily", "alert", "context"}
        for chunk in sample_chunks:
            assert chunk["metadata"]["type"] in valid_types

    def test_chunks_under_max_size(self, sample_chunks: list[dict[str, Any]]) -> None:
        for chunk in sample_chunks:
            assert len(chunk["text"]) <= 512
