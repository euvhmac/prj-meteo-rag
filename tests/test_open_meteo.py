"""Tests for the Open-Meteo API client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.data.open_meteo import (
    MG_CITIES,
    WMO_WEATHER_CODES,
    OpenMeteoClient,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_forecast_payload(city: str = "Belo Horizonte") -> dict:
    """Return a minimal valid Open-Meteo forecast response."""
    return {
        "latitude": -19.9167,
        "longitude": -43.9345,
        "timezone": "America/Sao_Paulo",
        "hourly": {
            "time": ["2026-01-01T12:00", "2026-01-01T13:00"],
            "temperature_2m": [28.5, 29.0],
            "apparent_temperature": [30.0, 30.5],
            "relative_humidity_2m": [70, 68],
            "precipitation": [0.0, 1.5],
            "rain": [0.0, 1.5],
            "wind_speed_10m": [15.0, 18.0],
            "wind_direction_10m": [90, 100],
            "weather_code": [61, 63],
            "cloud_cover": [80, 90],
        },
        "city": city,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOpenMeteoClientGetForecast:
    def test_returns_parsed_json_on_success(self):
        client = OpenMeteoClient()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_forecast_payload()
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.open_meteo.requests.get", return_value=mock_resp) as mock_get:
            result = client.get_forecast(-19.9167, -43.9345, hours=24)

        mock_get.assert_called_once()
        assert result["timezone"] == "America/Sao_Paulo"
        assert "hourly" in result

    def test_raises_on_http_error(self):
        import requests as req
        client = OpenMeteoClient()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("500")

        with patch("src.data.open_meteo.requests.get", return_value=mock_resp):
            with pytest.raises(req.HTTPError):
                client.get_forecast(-19.9167, -43.9345)

    def test_forecast_days_capped_at_7(self):
        client = OpenMeteoClient()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_forecast_payload()
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.open_meteo.requests.get", return_value=mock_resp) as mock_get:
            client.get_forecast(-19.9167, -43.9345, hours=300)

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["forecast_days"] <= 7


class TestOpenMeteoClientGetCityForecast:
    def test_valid_city_returns_forecast_with_city_key(self):
        client = OpenMeteoClient()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_forecast_payload("Belo Horizonte")
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.open_meteo.requests.get", return_value=mock_resp):
            result = client.get_city_forecast("Belo Horizonte")

        assert result["city"] == "Belo Horizonte"

    def test_unknown_city_raises_value_error(self):
        client = OpenMeteoClient()
        with pytest.raises(ValueError, match="Cidade"):
            client.get_city_forecast("Cidade Inexistente")


class TestOpenMeteoClientGetAllCitiesSummary:
    def test_returns_one_summary_per_successful_city(self):
        client = OpenMeteoClient()
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_forecast_payload()
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.open_meteo.requests.get", return_value=mock_resp):
            summaries = client.get_all_cities_summary()

        assert len(summaries) == len(MG_CITIES)
        assert all("summary" in s for s in summaries)

    def test_skips_failed_city(self):
        import requests as req
        client = OpenMeteoClient()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.ConnectionError("timeout")

        with patch("src.data.open_meteo.requests.get", return_value=mock_resp):
            summaries = client.get_all_cities_summary()

        assert summaries == []


class TestExtractCurrentSummary:
    def test_summary_contains_city_name(self):
        data = _make_forecast_payload("Belo Horizonte")
        result = OpenMeteoClient._extract_current_summary("Belo Horizonte", data)
        assert "Belo Horizonte" in result["summary"]

    def test_summary_contains_condition(self):
        data = _make_forecast_payload()
        result = OpenMeteoClient._extract_current_summary("Uberlândia", data)
        assert "condição" in result["summary"]

    def test_empty_time_list_returns_sem_dados(self):
        data = {"hourly": {"time": []}}
        result = OpenMeteoClient._extract_current_summary("Test City", data)
        assert "Sem dados" in result["summary"]

    def test_wmo_code_translated(self):
        assert WMO_WEATHER_CODES[61] == "chuva leve"
        assert WMO_WEATHER_CODES[95] == "trovoada"


class TestMGCities:
    def test_mg_cities_not_empty(self):
        assert len(MG_CITIES) >= 10

    def test_belo_horizonte_present(self):
        assert "Belo Horizonte" in MG_CITIES

    def test_coordinates_are_valid_floats(self):
        for city, coords in MG_CITIES.items():
            assert isinstance(coords["lat"], float), city
            assert isinstance(coords["lon"], float), city
            assert -30 <= coords["lat"] <= -15, city  # MG latitude range (southern hemisphere)
            assert -55 <= coords["lon"] <= -39, city  # MG longitude range
