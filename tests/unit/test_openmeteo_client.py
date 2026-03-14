"""Testes unitários para o cliente Open-Meteo.

Testa a conversão de dados, cache em memória, tratamento de erros
e normalização para o formato MeteoRAG.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from meteorag.api.openmeteo_client import (
    MG_CITIES,
    WMO_DESCRIPTIONS,
    WMO_RISK,
    OpenMeteoClient,
    _safe_index,
    wmo_risk,
    wmo_to_text,
)
from meteorag.config import Settings

# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════


@pytest.fixture()
def settings() -> Settings:
    """Settings com valores padrão para testes."""
    return Settings(
        anthropic_api_key="test-key",
        default_days_back=3,
    )


@pytest.fixture()
def client(settings: Settings) -> OpenMeteoClient:
    """Cliente Open-Meteo com settings de teste."""
    return OpenMeteoClient(settings)


@pytest.fixture()
def sample_openmeteo_response() -> dict[str, Any]:
    """Resposta mockada da API Open-Meteo (Forecast com past_days=3)."""
    return {
        "latitude": -21.75,
        "longitude": -43.375,
        "generationtime_ms": 1.5,
        "utc_offset_seconds": -10800,
        "timezone": "America/Sao_Paulo",
        "timezone_abbreviation": "-03",
        "elevation": 940.0,
        "current_units": {
            "time": "iso8601",
            "precipitation": "mm",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "wind_speed_10m": "km/h",
            "weather_code": "wmo code",
            "surface_pressure": "hPa",
        },
        "current": {
            "time": "2024-01-18T14:00",
            "precipitation": 0.0,
            "temperature_2m": 25.3,
            "relative_humidity_2m": 68,
            "wind_speed_10m": 12.5,
            "weather_code": 2,
            "surface_pressure": 912.0,
        },
        "hourly_units": {
            "time": "iso8601",
            "precipitation": "mm",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "wind_speed_10m": "km/h",
            "wind_direction_10m": "°",
            "surface_pressure": "hPa",
            "weather_code": "wmo code",
        },
        "hourly": {
            "time": [
                "2024-01-15T00:00",
                "2024-01-15T01:00",
                "2024-01-15T12:00",
                "2024-01-15T13:00",
                "2024-01-16T00:00",
                "2024-01-16T12:00",
                "2024-01-17T00:00",
                "2024-01-17T12:00",
                "2024-01-18T00:00",
                "2024-01-18T12:00",
            ],
            "precipitation": [0.0, 2.4, 15.6, 0.0, 0.0, 0.0, 1.2, 8.4, 0.0, 0.0],
            "temperature_2m": [
                19.5,
                19.0,
                24.5,
                23.1,
                18.2,
                26.8,
                20.1,
                22.3,
                21.0,
                25.3,
            ],
            "relative_humidity_2m": [85, 88, 72, 75, 90, 65, 82, 78, 80, 68],
            "wind_speed_10m": [5.0, 4.2, 12.0, 15.5, 3.6, 8.1, 6.2, 18.0, 4.0, 12.5],
            "wind_direction_10m": [180, 190, 270, 280, 150, 200, 160, 300, 170, 250],
            "surface_pressure": [
                912.5,
                912.3,
                910.2,
                911.0,
                913.0,
                912.8,
                911.5,
                910.0,
                912.0,
                912.0,
            ],
            "weather_code": [0, 51, 65, 61, 0, 0, 51, 82, 0, 2],
        },
        "daily_units": {
            "time": "iso8601",
            "precipitation_sum": "mm",
            "precipitation_hours": "h",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "wind_speed_10m_max": "km/h",
            "weather_code": "wmo code",
        },
        "daily": {
            "time": ["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18"],
            "precipitation_sum": [18.0, 0.0, 9.6, 0.0],
            "precipitation_hours": [3.0, 0.0, 2.0, 0.0],
            "temperature_2m_max": [24.5, 26.8, 22.3, 25.3],
            "temperature_2m_min": [19.0, 18.2, 20.1, 21.0],
            "wind_speed_10m_max": [15.5, 8.1, 18.0, 12.5],
            "weather_code": [65, 0, 82, 2],
        },
    }


@pytest.fixture()
def empty_openmeteo_response() -> dict[str, Any]:
    """Resposta vazia/mínima da API Open-Meteo."""
    return {}


# ═══════════════════════════════════════════════════════════
# Testes: WMO helpers
# ═══════════════════════════════════════════════════════════


class TestWMOHelpers:
    """Testes para funções de conversão de códigos WMO."""

    def test_wmo_to_text_known_code(self) -> None:
        """Código WMO conhecido retorna descrição correta."""
        assert wmo_to_text(0) == "céu limpo"
        assert wmo_to_text(65) == "chuva forte"
        assert wmo_to_text(95) == "trovoada"

    def test_wmo_to_text_none(self) -> None:
        """None retorna 'condição desconhecida'."""
        assert wmo_to_text(None) == "condição desconhecida"

    def test_wmo_to_text_unknown_code(self) -> None:
        """Código desconhecido retorna fallback com número."""
        assert wmo_to_text(999) == "código WMO 999"

    def test_wmo_to_text_all_codes_mapped(self) -> None:
        """Todos os códigos no dicionário retornam string não-vazia."""
        for code, desc in WMO_DESCRIPTIONS.items():
            assert isinstance(desc, str)
            assert len(desc) > 0
            assert wmo_to_text(code) == desc

    def test_wmo_risk_known(self) -> None:
        """Códigos com risco retornam nível correto."""
        assert wmo_risk(65) == "alto"
        assert wmo_risk(95) == "alto"
        assert wmo_risk(99) == "extremo"
        assert wmo_risk(63) == "moderado"

    def test_wmo_risk_none(self) -> None:
        """None retorna None."""
        assert wmo_risk(None) is None

    def test_wmo_risk_no_risk_code(self) -> None:
        """Código sem risco retorna None."""
        assert wmo_risk(0) is None
        assert wmo_risk(3) is None

    def test_wmo_risk_all_mapped(self) -> None:
        """Todos os códigos de risco estão mapeados."""
        for _code, level in WMO_RISK.items():
            assert level in ("moderado", "alto", "extremo")


# ═══════════════════════════════════════════════════════════
# Testes: _safe_index
# ═══════════════════════════════════════════════════════════


class TestSafeIndex:
    """Testes para a função _safe_index."""

    def test_valid_index(self) -> None:
        """Índice válido retorna valor correto."""
        assert _safe_index([10, 20, 30], 1) == 20

    def test_out_of_range(self) -> None:
        """Índice fora do range retorna None."""
        assert _safe_index([10, 20], 5) is None

    def test_none_array(self) -> None:
        """Array None retorna None."""
        assert _safe_index(None, 0) is None

    def test_empty_array(self) -> None:
        """Array vazio retorna None."""
        assert _safe_index([], 0) is None

    def test_first_element(self) -> None:
        """Acessa primeiro elemento."""
        assert _safe_index([42], 0) == 42


# ═══════════════════════════════════════════════════════════
# Testes: MG_CITIES
# ═══════════════════════════════════════════════════════════


class TestMGCities:
    """Testes para o dicionário de cidades."""

    def test_has_priority_cities(self) -> None:
        """Contém todas as cidades prioritárias."""
        assert "Juiz de Fora" in MG_CITIES
        assert "Ubá" in MG_CITIES
        assert "Barbacena" in MG_CITIES
        assert "Viçosa" in MG_CITIES
        assert "Cataguases" in MG_CITIES
        assert "Belo Horizonte" in MG_CITIES
        assert "Muriaé" in MG_CITIES

    def test_all_cities_have_required_fields(self) -> None:
        """Cada cidade tem lat, lon, altitude e region."""
        for city, info in MG_CITIES.items():
            assert "lat" in info, f"{city} faltando lat"
            assert "lon" in info, f"{city} faltando lon"
            assert "altitude" in info, f"{city} faltando altitude"
            assert "region" in info, f"{city} faltando region"

    def test_coordinates_in_valid_range(self) -> None:
        """Coordenadas estão no range válido para MG."""
        for city, info in MG_CITIES.items():
            assert -23.0 < info["lat"] < -18.0, f"{city}: lat {info['lat']} fora de MG"
            assert -46.0 < info["lon"] < -40.0, f"{city}: lon {info['lon']} fora de MG"

    def test_minimum_city_count(self) -> None:
        """Há pelo menos 7 cidades mapeadas."""
        assert len(MG_CITIES) >= 7


# ═══════════════════════════════════════════════════════════
# Testes: OpenMeteoClient
# ═══════════════════════════════════════════════════════════


class TestOpenMeteoClient:
    """Testes para o cliente Open-Meteo."""

    def test_get_coordinates_valid(self, client: OpenMeteoClient) -> None:
        """Coordenadas de cidade conhecida são retornadas."""
        lat, lon = client._get_coordinates("Juiz de Fora")
        assert lat == pytest.approx(-21.7609)
        assert lon == pytest.approx(-43.3496)

    def test_get_coordinates_unknown(self, client: OpenMeteoClient) -> None:
        """Cidade desconhecida levanta ValueError."""
        with pytest.raises(ValueError, match="Cidade não mapeada"):
            client._get_coordinates("Cidade Inexistente")

    def test_cache_key_format(self, client: OpenMeteoClient) -> None:
        """Chave de cache tem formato correto."""
        key = client._cache_key("Juiz de Fora", 7)
        assert key == "Juiz de Fora:7"

    def test_cache_set_and_get(self, client: OpenMeteoClient) -> None:
        """Cache armazena e recupera dados."""
        data = {"test": True}
        client._set_cached("key1", data)
        assert client._get_cached("key1") == data

    def test_cache_miss(self, client: OpenMeteoClient) -> None:
        """Cache miss retorna None."""
        assert client._get_cached("nonexistent") is None

    def test_clear_cache(self, client: OpenMeteoClient) -> None:
        """Clear cache remove todos os dados."""
        client._set_cached("key1", {"a": 1})
        client._set_cached("key2", {"b": 2})
        client.clear_cache()
        assert client._get_cached("key1") is None
        assert client._get_cached("key2") is None


class TestOpenMeteoGetWeather:
    """Testes para get_weather (chamada HTTP mockada)."""

    def test_success(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Retorna dados corretamente quando API responde."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_openmeteo_response
        mock_resp.text = "{}"
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp):
            data = client.get_weather("Juiz de Fora", days_back=3)

        assert "hourly" in data
        assert "daily" in data
        assert "current" in data

    def test_uses_cache(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Segunda chamada usa cache em vez de HTTP."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_openmeteo_response
        mock_resp.text = "{}"
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            client.get_weather("Juiz de Fora", days_back=3)
            client.get_weather("Juiz de Fora", days_back=3)

        assert mock_get.call_count == 1

    def test_http_error_returns_empty(self, client: OpenMeteoClient) -> None:
        """Erro HTTP retorna dict vazio."""
        import requests

        with patch.object(
            client._session,
            "get",
            side_effect=requests.exceptions.ConnectionError("timeout"),
        ):
            data = client.get_weather("Juiz de Fora", days_back=3)

        assert data == {}

    def test_default_days_back(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Usa default_days_back quando não especificado."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = sample_openmeteo_response
        mock_resp.text = "{}"
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            client.get_weather("Juiz de Fora")

        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["past_days"] == 3  # settings.default_days_back


class TestOpenMeteoGetDailySummaries:
    """Testes para get_daily_summaries."""

    def test_parses_daily_data(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Parseia dados diários corretamente."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            summaries = client.get_daily_summaries("Juiz de Fora", days_back=3)

        assert len(summaries) == 4
        s1 = summaries[0]
        assert s1["city"] == "Juiz de Fora"
        assert s1["station_code"] == "Open-Meteo"
        assert s1["date"] == "2024-01-15"
        assert s1["total_rain_mm"] == 18.0
        assert s1["max_temp_c"] == 24.5
        assert s1["min_temp_c"] == 19.0
        assert s1["weather_code"] == 65
        assert s1["weather_description"] == "chuva forte"

    def test_empty_response(self, client: OpenMeteoClient) -> None:
        """Resposta vazia retorna lista vazia."""
        with patch.object(client, "get_weather", return_value={}):
            summaries = client.get_daily_summaries("Juiz de Fora")

        assert summaries == []

    def test_avg_humidity_calculated(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Umidade média é calculada a partir de dados horários."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            summaries = client.get_daily_summaries("Juiz de Fora")

        # 15/01: hours 00, 01, 12, 13 → humidity: 85, 88, 72, 75 → avg = 80.0
        assert summaries[0]["avg_humidity_pct"] == 80.0

    def test_observation_count(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """observation_count conta horas do dia corretamente."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            summaries = client.get_daily_summaries("Juiz de Fora")

        # 15/01 tem 4 horas de dados na fixture
        assert summaries[0]["observation_count"] == 4
        # 16/01 tem 2 horas
        assert summaries[1]["observation_count"] == 2

    def test_wind_max_preserved(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """wind_max_kmh é preservado do daily."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            summaries = client.get_daily_summaries("Juiz de Fora")

        assert summaries[0]["wind_max_kmh"] == 15.5

    def test_no_daily_key(self, client: OpenMeteoClient) -> None:
        """Resposta sem 'daily' retorna lista vazia."""
        with patch.object(client, "get_weather", return_value={"hourly": {}}):
            summaries = client.get_daily_summaries("Juiz de Fora")

        assert summaries == []


class TestOpenMeteoGetObservations:
    """Testes para get_observations."""

    def test_parses_hourly_data(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Parseia dados horários corretamente."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            obs = client.get_observations("Juiz de Fora", days_back=3)

        assert len(obs) == 10
        o1 = obs[0]
        assert o1["station_code"] == "Open-Meteo"
        assert o1["date"] == "2024-01-15"
        assert o1["time"] == "00:00"
        assert o1["rain_mm"] == 0.0
        assert o1["temp_c"] == 19.5
        assert o1["humidity_pct"] == 85

    def test_wind_converted_to_ms(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Vento é convertido de km/h para m/s."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            obs = client.get_observations("Juiz de Fora")

        # First obs: 5.0 km/h → 5.0/3.6 = 1.4 m/s
        assert obs[0]["wind_speed_ms"] == pytest.approx(1.4, abs=0.1)

    def test_weather_code_included(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """weather_code é incluído nas observações."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            obs = client.get_observations("Juiz de Fora")

        assert obs[0]["weather_code"] == 0  # céu limpo
        assert obs[2]["weather_code"] == 65  # chuva forte

    def test_empty_response(self, client: OpenMeteoClient) -> None:
        """Resposta vazia retorna lista vazia."""
        with patch.object(client, "get_weather", return_value={}):
            obs = client.get_observations("Juiz de Fora")

        assert obs == []

    def test_time_format(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Formato de hora é HH:MM."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            obs = client.get_observations("Juiz de Fora")

        assert obs[2]["time"] == "12:00"
        assert obs[3]["time"] == "13:00"

    def test_temp_max_min_none(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """temp_max_c e temp_min_c são sempre None (não disponíveis horariamente)."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            obs = client.get_observations("Juiz de Fora")

        for o in obs:
            assert o["temp_max_c"] is None
            assert o["temp_min_c"] is None


class TestOpenMeteoGetCurrent:
    """Testes para get_current."""

    def test_returns_current_conditions(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Retorna condições atuais normalizadas."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            current = client.get_current("Juiz de Fora")

        assert current is not None
        assert current["city"] == "Juiz de Fora"
        assert current["temp_c"] == 25.3
        assert current["humidity_pct"] == 68
        assert current["weather_code"] == 2
        assert current["weather_description"] == "parcialmente nublado"

    def test_wind_converted(
        self,
        client: OpenMeteoClient,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Vento convertido de km/h para m/s."""
        with patch.object(client, "get_weather", return_value=sample_openmeteo_response):
            current = client.get_current("Juiz de Fora")

        assert current is not None
        # 12.5 km/h → 3.5 m/s
        assert current["wind_speed_ms"] == pytest.approx(3.5, abs=0.1)

    def test_returns_none_on_empty(self, client: OpenMeteoClient) -> None:
        """Retorna None se API falhar."""
        with patch.object(client, "get_weather", return_value={}):
            current = client.get_current("Juiz de Fora")

        assert current is None


class TestOpenMeteoHelpers:
    """Testes para métodos auxiliares estáticos."""

    def test_calc_daily_avg_humidity(
        self,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Calcula média de umidade para um dia específico."""
        avg = OpenMeteoClient._calc_daily_avg_humidity(sample_openmeteo_response, "2024-01-15")
        # Hours 00, 01, 12, 13 → humidity: 85, 88, 72, 75 → avg = 80.0
        assert avg == 80.0

    def test_calc_daily_avg_humidity_no_data(self) -> None:
        """Retorna None se não houver dados para a data."""
        avg = OpenMeteoClient._calc_daily_avg_humidity(
            {"hourly": {"time": [], "relative_humidity_2m": []}},
            "2024-01-15",
        )
        assert avg is None

    def test_count_hourly_for_date(
        self,
        sample_openmeteo_response: dict[str, Any],
    ) -> None:
        """Conta horas de dados para um dia."""
        count = OpenMeteoClient._count_hourly_for_date(sample_openmeteo_response, "2024-01-15")
        assert count == 4

    def test_count_hourly_no_data(self) -> None:
        """Retorna 0 se não houver dados."""
        count = OpenMeteoClient._count_hourly_for_date({"hourly": {"time": []}}, "2024-01-15")
        assert count == 0
