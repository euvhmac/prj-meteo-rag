"""Testes unitários para inmet_client.py.

Todos os testes usam fixtures locais — sem requisições HTTP reais.
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

import requests

from meteorag.api.inmet_client import (
    MG_PRIORITY_STATIONS,
    INMETClient,
    _CacheEntry,
    get_daily_summary,
    parse_observation,
    parse_value,
)
from meteorag.config import Settings

# ══════════════════════════════════════════════════════════
# parse_value
# ══════════════════════════════════════════════════════════


class TestParseValue:
    """Testes para a função parse_value."""

    def test_valid_float_string(self) -> None:
        assert parse_value("22.5") == 22.5

    def test_valid_int_string(self) -> None:
        assert parse_value("100") == 100.0

    def test_valid_zero(self) -> None:
        assert parse_value("0.0") == 0.0

    def test_none_returns_none(self) -> None:
        assert parse_value(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_value("") is None

    def test_whitespace_returns_none(self) -> None:
        assert parse_value("   ") is None

    def test_negative_9999_returns_none(self) -> None:
        assert parse_value("-9999") is None

    def test_positive_9999_returns_none(self) -> None:
        assert parse_value("9999") is None

    def test_float_9999_returns_none(self) -> None:
        assert parse_value("-9999.0") is None

    def test_numeric_int(self) -> None:
        assert parse_value(42) == 42.0

    def test_numeric_float(self) -> None:
        assert parse_value(3.14) == 3.14

    def test_non_numeric_string_returns_none(self) -> None:
        assert parse_value("abc") is None

    def test_negative_value_is_valid(self) -> None:
        assert parse_value("-5.3") == -5.3


# ══════════════════════════════════════════════════════════
# parse_observation
# ══════════════════════════════════════════════════════════


class TestParseObservation:
    """Testes para a função parse_observation."""

    def test_normalizes_valid_observation(
        self, sample_hourly_observations: list[dict[str, Any]]
    ) -> None:
        raw = sample_hourly_observations[0]
        parsed = parse_observation(raw)

        assert parsed["station_code"] == "A518"
        assert parsed["date"] == "2024-01-15"
        assert parsed["time"] == "1200 UTC"
        assert parsed["rain_mm"] == 2.4
        assert parsed["temp_c"] == 22.5
        assert parsed["humidity_pct"] == 78.0

    def test_normalizes_nulls(self, sample_observations_with_nulls: list[dict[str, Any]]) -> None:
        raw = sample_observations_with_nulls[0]
        parsed = parse_observation(raw)

        assert parsed["rain_mm"] is None  # None original
        assert parsed["temp_c"] is None  # -9999
        assert parsed["temp_max_c"] is None  # 9999
        assert parsed["temp_min_c"] is None  # ""
        assert parsed["humidity_pct"] is None  # None
        assert parsed["pressure_hpa"] is None  # -9999
        assert parsed["wind_speed_ms"] == 0.0  # "0.0" válido

    def test_all_fields_present(self, sample_hourly_observations: list[dict[str, Any]]) -> None:
        parsed = parse_observation(sample_hourly_observations[0])
        expected_keys = {
            "station_code",
            "date",
            "time",
            "rain_mm",
            "temp_c",
            "temp_max_c",
            "temp_min_c",
            "humidity_pct",
            "wind_speed_ms",
            "wind_dir_deg",
            "pressure_hpa",
            "radiation_kjm2",
        }
        assert set(parsed.keys()) == expected_keys

    def test_empty_dict_returns_defaults(self) -> None:
        parsed = parse_observation({})
        assert parsed["station_code"] == ""
        assert parsed["date"] == ""
        assert parsed["rain_mm"] is None


# ══════════════════════════════════════════════════════════
# get_daily_summary
# ══════════════════════════════════════════════════════════


class TestGetDailySummary:
    """Testes para a função get_daily_summary."""

    def test_aggregates_correctly(self, sample_hourly_observations: list[dict[str, Any]]) -> None:
        observations = [parse_observation(o) for o in sample_hourly_observations]
        summary = get_daily_summary(observations, "Juiz de Fora", "A518", "2024-01-15")

        assert summary["city"] == "Juiz de Fora"
        assert summary["station_code"] == "A518"
        assert summary["date"] == "2024-01-15"
        assert summary["total_rain_mm"] == 18.0  # 2.4 + 0.0 + 15.6
        assert summary["max_temp_c"] == 24.5
        assert summary["min_temp_c"] == 20.1
        assert summary["observation_count"] == 3

    def test_single_observation_day(self, sample_hourly_observations: list[dict[str, Any]]) -> None:
        observations = [parse_observation(o) for o in sample_hourly_observations]
        summary = get_daily_summary(observations, "Juiz de Fora", "A518", "2024-01-16")

        assert summary["observation_count"] == 1
        assert summary["total_rain_mm"] == 0.0

    def test_no_observations_for_date(
        self, sample_hourly_observations: list[dict[str, Any]]
    ) -> None:
        observations = [parse_observation(o) for o in sample_hourly_observations]
        summary = get_daily_summary(observations, "Juiz de Fora", "A518", "2024-12-31")

        assert summary["observation_count"] == 0
        assert summary["total_rain_mm"] is None

    def test_nulls_excluded_from_aggregation(
        self, sample_observations_with_nulls: list[dict[str, Any]]
    ) -> None:
        observations = [parse_observation(o) for o in sample_observations_with_nulls]
        summary = get_daily_summary(observations, "Juiz de Fora", "A518", "2024-01-17")

        assert summary["observation_count"] == 2
        # Todos os valores numéricos são None ou inválidos
        assert summary["total_rain_mm"] is None
        assert summary["max_temp_c"] is None
        assert summary["min_temp_c"] is None


# ══════════════════════════════════════════════════════════
# _CacheEntry
# ══════════════════════════════════════════════════════════


class TestCacheEntry:
    """Testes para a classe _CacheEntry."""

    def test_valid_within_ttl(self) -> None:
        entry = _CacheEntry(data={"test": True}, ttl_seconds=60)
        assert entry.is_valid is True

    def test_expired_after_ttl(self) -> None:
        entry = _CacheEntry(data={"test": True}, ttl_seconds=0)
        # TTL de 0 expira imediatamente (monotonic avança)
        time.sleep(0.01)
        assert entry.is_valid is False

    def test_stores_data(self) -> None:
        data = [1, 2, 3]
        entry = _CacheEntry(data=data, ttl_seconds=60)
        assert entry.data == [1, 2, 3]


# ══════════════════════════════════════════════════════════
# INMETClient
# ══════════════════════════════════════════════════════════


class TestINMETClient:
    """Testes para a classe INMETClient (com mock de HTTP)."""

    def _make_client(self) -> INMETClient:
        """Cria um cliente com settings padrão para testes."""
        settings = Settings(
            inmet_base_url="https://apitempo.inmet.gov.br",
            inmet_cache_ttl_seconds=60,
            inmet_retry_max=2,
            inmet_timeout_seconds=5,
        )
        return INMETClient(settings=settings)

    def test_get_stations_returns_list(self, sample_stations: list[dict[str, Any]]) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_stations
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            result = client.get_stations()

        assert len(result) == 5
        assert result[0]["CD_ESTACAO"] == "A518"

    def test_get_mg_stations_filters_correctly(self, sample_stations: list[dict[str, Any]]) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_stations
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            mg = client.get_mg_stations()

        assert len(mg) == 4
        assert all(s["SG_ESTADO"] == "MG" for s in mg)

    def test_get_priority_stations(self, sample_stations: list[dict[str, Any]]) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_stations
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            priority = client.get_priority_stations()

        codes = {s["CD_ESTACAO"] for s in priority}
        # A518, A519, A520, A521 estão nos samples E no MG_PRIORITY_STATIONS
        assert codes.issubset(set(MG_PRIORITY_STATIONS.keys()))

    def test_http_204_returns_empty_list(self) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with patch.object(client._session, "get", return_value=mock_resp):
            result = client.get_alerts("MG")

        assert result == []

    def test_cache_hit(self, sample_stations: list[dict[str, Any]]) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_stations
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            # Primeira chamada
            client.get_stations()
            # Segunda chamada (deve vir do cache)
            client.get_stations()

        assert mock_get.call_count == 1

    def test_clear_cache(self, sample_stations: list[dict[str, Any]]) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_stations
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            client.get_stations()
            client.clear_cache()
            client.get_stations()

        assert mock_get.call_count == 2

    def test_timeout_retries(self) -> None:
        client = self._make_client()

        with (
            patch.object(
                client._session,
                "get",
                side_effect=requests.exceptions.Timeout("timeout"),
            ) as mock_get,
            patch("meteorag.api.inmet_client.time.sleep"),
        ):
            result = client.get_stations()

        assert result == []
        assert mock_get.call_count == 2  # max_retries=2

    def test_http_500_retries(self) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)

        with (
            patch.object(client._session, "get", return_value=mock_resp) as mock_get,
            patch("meteorag.api.inmet_client.time.sleep"),
        ):
            result = client.get_stations()

        assert result == []
        assert mock_get.call_count == 2

    def test_http_404_no_retry(self) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)

        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            result = client.get_stations()

        assert result == []
        assert mock_get.call_count == 1  # Sem retry para 4xx

    def test_get_observations_normalizes(
        self, sample_hourly_observations: list[dict[str, Any]]
    ) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_hourly_observations
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            from datetime import date

            obs = client.get_observations(
                "A518",
                start_date=date(2024, 1, 15),
                end_date=date(2024, 1, 16),
            )

        assert len(obs) == 4
        assert obs[0]["station_code"] == "A518"
        assert obs[0]["rain_mm"] == 2.4

    def test_get_station_name_priority(self) -> None:
        client = self._make_client()
        assert client.get_station_name("A518") == "Juiz de Fora"

    def test_get_station_name_from_api(self, sample_stations: list[dict[str, Any]]) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_stations
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            name = client.get_station_name("A001")

        assert name == "BRASILIA"

    def test_get_station_name_unknown(self) -> None:
        client = self._make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            name = client.get_station_name("ZZZZ")

        assert name == "ZZZZ"

    def test_parse_alert(self, sample_alerts: list[dict[str, Any]]) -> None:
        client = self._make_client()
        parsed = client.parse_alert(sample_alerts[0])

        assert parsed["id"] == "1234"
        assert parsed["severity"] == "Perigo"
        assert parsed["event"] == "Chuvas Intensas"
        assert "Juiz de Fora" in parsed["cities"]

    def test_alert_matches_state(self) -> None:
        alert_mg = {"estado": "MG", "descricao": "teste"}
        alert_sp = {"estado": "SP", "descricao": "teste"}

        assert INMETClient._alert_matches_state(alert_mg, "MG") is True
        assert INMETClient._alert_matches_state(alert_sp, "MG") is False
        assert INMETClient._alert_matches_state(alert_mg, "mg") is True


# ══════════════════════════════════════════════════════════
# Fixture sanity checks (preservados da Sprint 0)
# ══════════════════════════════════════════════════════════


class TestSampleFixtures:
    """Testes de sanidade para verificar que as fixtures estão funcionando."""

    def test_stations_fixture_has_data(self, sample_stations: list[dict[str, Any]]) -> None:
        assert len(sample_stations) > 0

    def test_stations_have_required_fields(self, sample_stations: list[dict[str, Any]]) -> None:
        required_fields = {"CD_ESTACAO", "DC_NOME", "SG_ESTADO"}
        for station in sample_stations:
            assert required_fields.issubset(station.keys())

    def test_mg_stations_present(self, sample_stations: list[dict[str, Any]]) -> None:
        mg_stations = [s for s in sample_stations if s["SG_ESTADO"] == "MG"]
        assert len(mg_stations) >= 3

    def test_observations_have_required_fields(
        self, sample_hourly_observations: list[dict[str, Any]]
    ) -> None:
        required_fields = {"CD_ESTACAO", "DT_MEDICAO", "HR_MEDICAO", "CHUVA", "TEM_INS"}
        for obs in sample_hourly_observations:
            assert required_fields.issubset(obs.keys())

    def test_observations_with_nulls_have_invalid_values(
        self, sample_observations_with_nulls: list[dict[str, Any]]
    ) -> None:
        obs = sample_observations_with_nulls[0]
        has_invalid = any(
            v is None or v == "" or v in ("-9999", "9999")
            for v in [obs["CHUVA"], obs["TEM_INS"], obs["TEM_MAX"], obs["TEM_MIN"]]
        )
        assert has_invalid

    def test_alerts_have_required_fields(self, sample_alerts: list[dict[str, Any]]) -> None:
        required_fields = {"descricao", "severidade", "evento", "municipios"}
        for alert in sample_alerts:
            assert required_fields.issubset(alert.keys())

    def test_empty_alerts_is_empty(self, empty_alerts: list[dict[str, Any]]) -> None:
        assert empty_alerts == []
