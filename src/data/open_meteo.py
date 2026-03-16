"""Open-Meteo API client for weather data in Minas Gerais."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

import requests

OPEN_METEO_BASE_URL = os.getenv(
    "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1"
)

# Key cities in Minas Gerais with their coordinates
MG_CITIES: dict[str, dict[str, float]] = {
    "Belo Horizonte": {"lat": -19.9167, "lon": -43.9345},
    "Uberlândia": {"lat": -18.9186, "lon": -48.2772},
    "Contagem": {"lat": -19.9317, "lon": -44.0536},
    "Juiz de Fora": {"lat": -21.7642, "lon": -43.3503},
    "Betim": {"lat": -19.9678, "lon": -44.1983},
    "Montes Claros": {"lat": -16.7282, "lon": -43.8616},
    "Ribeirão das Neves": {"lat": -19.7625, "lon": -44.0878},
    "Uberaba": {"lat": -19.7478, "lon": -47.9317},
    "Governador Valadares": {"lat": -18.8511, "lon": -41.9494},
    "Ipatinga": {"lat": -19.4683, "lon": -42.5367},
    "Sete Lagoas": {"lat": -19.4658, "lon": -44.2494},
    "Divinópolis": {"lat": -20.1394, "lon": -44.8828},
    "Teófilo Otoni": {"lat": -17.8578, "lon": -41.5053},
    "Poços de Caldas": {"lat": -21.7878, "lon": -46.5614},
    "Patos de Minas": {"lat": -18.5786, "lon": -46.5183},
    "Coronel Fabriciano": {"lat": -19.5181, "lon": -42.6278},
    "Barbacena": {"lat": -21.2258, "lon": -43.7733},
    "Lavras": {"lat": -21.2456, "lon": -44.9997},
    "Varginha": {"lat": -21.5514, "lon": -45.4308},
    "Itabira": {"lat": -19.6189, "lon": -43.2269},
}

WEATHER_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "wind_speed_10m",
    "wind_direction_10m",
    "weather_code",
    "cloud_cover",
    "apparent_temperature",
]

WMO_WEATHER_CODES: dict[int, str] = {
    0: "céu limpo",
    1: "principalmente limpo",
    2: "parcialmente nublado",
    3: "nublado",
    45: "nevoeiro",
    48: "nevoeiro com geada",
    51: "garoa leve",
    53: "garoa moderada",
    55: "garoa intensa",
    61: "chuva leve",
    63: "chuva moderada",
    65: "chuva intensa",
    71: "neve leve",
    73: "neve moderada",
    75: "neve intensa",
    80: "pancadas de chuva leve",
    81: "pancadas de chuva moderada",
    82: "pancadas de chuva violenta",
    95: "trovoada",
    96: "trovoada com granizo leve",
    99: "trovoada com granizo intenso",
}


class OpenMeteoClient:
    """Client for the Open-Meteo free weather API."""

    def __init__(self, base_url: str = OPEN_METEO_BASE_URL, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_forecast(
        self, lat: float, lon: float, hours: int = 24
    ) -> dict[str, Any]:
        """Fetch hourly weather forecast for a given location.

        Args:
            lat: Latitude of the location.
            lon: Longitude of the location.
            hours: Number of forecast hours to retrieve (max 168).

        Returns:
            Parsed JSON response from Open-Meteo.

        Raises:
            requests.HTTPError: If the API returns a non-2xx status.
        """
        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(WEATHER_VARIABLES),
            "timezone": "America/Sao_Paulo",
            "forecast_days": max(1, min(hours // 24 + 1, 7)),
        }
        response = requests.get(
            f"{self.base_url}/forecast", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_city_forecast(self, city_name: str, hours: int = 24) -> dict[str, Any]:
        """Fetch forecast for a known Minas Gerais city by name.

        Args:
            city_name: City name (must be in MG_CITIES).
            hours: Number of forecast hours.

        Returns:
            Dict with city info and forecast data.

        Raises:
            ValueError: If city_name is not found in MG_CITIES.
            requests.HTTPError: If the API returns a non-2xx status.
        """
        coords = MG_CITIES.get(city_name)
        if coords is None:
            raise ValueError(
                f"Cidade '{city_name}' não encontrada. "
                f"Disponíveis: {sorted(MG_CITIES.keys())}"
            )
        forecast = self.get_forecast(coords["lat"], coords["lon"], hours=hours)
        forecast["city"] = city_name
        return forecast

    def get_all_cities_summary(self) -> list[dict[str, Any]]:
        """Fetch a brief weather summary for all MG cities.

        Returns a list of plain-text summaries for use in RAG documents.
        """
        summaries: list[dict[str, Any]] = []
        for city, coords in MG_CITIES.items():
            try:
                data = self.get_forecast(coords["lat"], coords["lon"], hours=6)
                summary = self._extract_current_summary(city, data)
                summaries.append(summary)
            except requests.RequestException:
                continue
        return summaries

    @staticmethod
    def _extract_current_summary(city: str, data: dict[str, Any]) -> dict[str, Any]:
        """Extract the most recent hourly observation from forecast data."""
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return {"city": city, "summary": f"Sem dados disponíveis para {city}."}

        now_str = datetime.now(tz=ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%dT%H")
        idx = 0
        for i, t in enumerate(times):
            if t.startswith(now_str):
                idx = i
                break

        def _val(key: str) -> Any:
            vals = hourly.get(key, [])
            return vals[idx] if idx < len(vals) else None

        temp = _val("temperature_2m")
        feels = _val("apparent_temperature")
        rain = _val("rain")
        precip = _val("precipitation")
        humidity = _val("relative_humidity_2m")
        wind = _val("wind_speed_10m")
        code = _val("weather_code")
        condition = WMO_WEATHER_CODES.get(int(code), "desconhecido") if code is not None else "desconhecido"

        parts = [f"Cidade: {city}"]
        if temp is not None:
            parts.append(f"temperatura {temp:.1f}°C")
        if feels is not None:
            parts.append(f"sensação térmica {feels:.1f}°C")
        if humidity is not None:
            parts.append(f"umidade {humidity:.0f}%")
        if wind is not None:
            parts.append(f"vento {wind:.1f} km/h")
        if precip is not None:
            parts.append(f"precipitação {precip:.1f} mm")
        if rain is not None and rain > 0:
            parts.append(f"chuva {rain:.1f} mm")
        parts.append(f"condição: {condition}")

        return {
            "city": city,
            "temperature": temp,
            "humidity": humidity,
            "rain": rain,
            "precipitation": precip,
            "wind_speed": wind,
            "condition": condition,
            "summary": ". ".join(parts) + ".",
        }
