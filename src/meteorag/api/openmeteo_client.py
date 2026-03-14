"""Cliente HTTP para a API Open-Meteo.

Fonte principal de dados meteorológicos do MeteoRAG.
API pública, sem autenticação, gratuita para uso não-comercial.

Variáveis horarias:
    precipitation, temperature_2m, relative_humidity_2m,
    wind_speed_10m, wind_direction_10m, surface_pressure, weather_code.

Variáveis diárias:
    precipitation_sum, precipitation_hours, temperature_2m_max,
    temperature_2m_min, wind_speed_10m_max, weather_code.
"""

from __future__ import annotations

import logging
import time
from typing import Any, ClassVar

import requests

from meteorag.config import Settings

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Cidades monitoradas — coordenadas para Open-Meteo
# ═══════════════════════════════════════════════════════════

MG_CITIES: dict[str, dict[str, Any]] = {
    "Juiz de Fora": {
        "lat": -21.7609,
        "lon": -43.3496,
        "altitude": 939,
        "region": "Zona da Mata",
    },
    "Ubá": {
        "lat": -21.1183,
        "lon": -42.9404,
        "altitude": 251,
        "region": "Zona da Mata",
    },
    "Barbacena": {
        "lat": -21.2258,
        "lon": -43.7736,
        "altitude": 1126,
        "region": "Campo das Vertentes",
    },
    "Muriaé": {
        "lat": -21.1322,
        "lon": -42.3670,
        "altitude": 256,
        "region": "Zona da Mata",
    },
    "Belo Horizonte": {
        "lat": -19.9167,
        "lon": -43.9345,
        "altitude": 915,
        "region": "Metropolitana",
    },
    "Viçosa": {
        "lat": -20.7546,
        "lon": -42.8825,
        "altitude": 649,
        "region": "Zona da Mata",
    },
    "Cataguases": {
        "lat": -21.3917,
        "lon": -42.6961,
        "altitude": 215,
        "region": "Zona da Mata",
    },
}

# ═══════════════════════════════════════════════════════════
# WMO Weather Codes (ISO 4677)
# ═══════════════════════════════════════════════════════════

WMO_DESCRIPTIONS: dict[int, str] = {
    0: "céu limpo",
    1: "majoritariamente limpo",
    2: "parcialmente nublado",
    3: "nublado",
    45: "neblina",
    48: "neblina com geada",
    51: "garoa fraca",
    53: "garoa moderada",
    55: "garoa intensa",
    56: "garoa congelante fraca",
    57: "garoa congelante intensa",
    61: "chuva fraca",
    63: "chuva moderada",
    65: "chuva forte",
    66: "chuva congelante fraca",
    67: "chuva congelante intensa",
    71: "nevada fraca",
    73: "nevada moderada",
    75: "nevada forte",
    77: "grãos de neve",
    80: "pancadas fracas",
    81: "pancadas moderadas",
    82: "pancadas violentas",
    85: "pancadas de neve fracas",
    86: "pancadas de neve fortes",
    95: "trovoada",
    96: "trovoada com granizo",
    99: "trovoada com granizo forte",
}

WMO_RISK: dict[int, str] = {
    63: "moderado",
    65: "alto",
    67: "alto",
    81: "moderado",
    82: "alto",
    95: "alto",
    96: "extremo",
    99: "extremo",
}


def wmo_to_text(code: int | None) -> str:
    """Converte código WMO para descrição textual em PT-BR.

    Args:
        code: Código WMO ou ``None``.

    Returns:
        Descrição textual da condição meteorológica.
    """
    if code is None:
        return "condição desconhecida"
    return WMO_DESCRIPTIONS.get(int(code), f"código WMO {code}")


def wmo_risk(code: int | None) -> str | None:
    """Retorna nível de risco associado ao código WMO.

    Args:
        code: Código WMO.

    Returns:
        Nível de risco (moderado/alto/extremo) ou ``None``.
    """
    if code is None:
        return None
    return WMO_RISK.get(int(code))


# ═══════════════════════════════════════════════════════════
# Funções auxiliares de módulo
# ═══════════════════════════════════════════════════════════


def _safe_index(arr: list[Any] | None, idx: int) -> Any:
    """Acessa lista com segurança, retornando ``None`` se inválido.

    Args:
        arr: Lista de valores.
        idx: Índice desejado.

    Returns:
        Valor no índice ou ``None``.
    """
    if arr is None or idx >= len(arr):
        return None
    return arr[idx]


# ═══════════════════════════════════════════════════════════
# Cliente Open-Meteo
# ═══════════════════════════════════════════════════════════


class OpenMeteoClient:
    """Cliente HTTP para a API Open-Meteo.

    Busca dados meteorológicos (hourly, daily, current) para
    as cidades monitoradas em Minas Gerais.

    Inclui cache em memória com TTL configurável para evitar
    chamadas redundantes à API.

    Args:
        settings: Configurações do projeto (opcional).

    Example:
        >>> client = OpenMeteoClient()
        >>> summaries = client.get_daily_summaries("Juiz de Fora")
        >>> len(summaries) > 0
        True
    """

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    HOURLY_VARS: ClassVar[list[str]] = [
        "precipitation",
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "wind_direction_10m",
        "surface_pressure",
        "weather_code",
    ]

    DAILY_VARS: ClassVar[list[str]] = [
        "precipitation_sum",
        "precipitation_hours",
        "temperature_2m_max",
        "temperature_2m_min",
        "wind_speed_10m_max",
        "weather_code",
    ]

    CURRENT_VARS: ClassVar[list[str]] = [
        "precipitation",
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "weather_code",
        "surface_pressure",
    ]

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "MeteoRAG/1.0"
        self.timeout = self._settings.openmeteo_timeout_seconds

        # Cache: {key -> (timestamp, data)}
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._cache_ttl = float(self._settings.inmet_cache_ttl_seconds)

    def _get_coordinates(self, city: str) -> tuple[float, float]:
        """Retorna (lat, lon) para uma cidade mapeada.

        Args:
            city: Nome da cidade.

        Returns:
            Tupla com latitude e longitude.

        Raises:
            ValueError: Se a cidade não está mapeada em ``MG_CITIES``.
        """
        info = MG_CITIES.get(city)
        if info is None:
            raise ValueError(f"Cidade não mapeada: {city}")
        return info["lat"], info["lon"]

    def _cache_key(self, city: str, days_back: int) -> str:
        """Gera chave de cache para uma consulta."""
        return f"{city}:{days_back}"

    def _get_cached(self, key: str) -> dict[str, Any] | None:
        """Retorna dados do cache se ainda válidos."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.monotonic() - ts > self._cache_ttl:
            del self._cache[key]
            return None
        return data

    def _set_cached(self, key: str, data: dict[str, Any]) -> None:
        """Armazena dados no cache."""
        self._cache[key] = (time.monotonic(), data)

    def clear_cache(self) -> None:
        """Limpa o cache em memória."""
        self._cache.clear()

    def get_weather(self, city: str, days_back: int | None = None) -> dict[str, Any]:
        """Busca dados completos (hourly + daily + current) via Forecast API.

        Usa ``past_days`` do Open-Meteo para obter dados recentes sem
        necessidade de calcular datas manualmente.

        Args:
            city: Nome da cidade (deve estar em ``MG_CITIES``).
            days_back: Dias retroativos (default: ``default_days_back``).

        Returns:
            JSON da resposta da API ou ``{}`` em caso de erro.
        """
        if days_back is None:
            days_back = self._settings.default_days_back

        # Verifica cache
        cache_key = self._cache_key(city, days_back)
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug("Cache hit para %s (days_back=%d)", city, days_back)
            return cached

        lat, lon = self._get_coordinates(city)

        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(self.HOURLY_VARS),
            "daily": ",".join(self.DAILY_VARS),
            "current": ",".join(self.CURRENT_VARS),
            "past_days": days_back,
            "forecast_days": 1,
            "timezone": "America/Sao_Paulo",
            "cell_selection": "land",
        }

        try:
            response = self._session.get(self.FORECAST_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            self._set_cached(cache_key, data)
            logger.info(
                "Open-Meteo dados recebidos para %s: %d bytes",
                city,
                len(response.text),
            )
            return data

        except requests.exceptions.RequestException as exc:
            logger.error("Open-Meteo request falhou para %s: %s", city, exc)
            return {}

    def get_daily_summaries(
        self,
        city: str,
        days_back: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna sumários diários normalizados para o formato MeteoRAG.

        Output compatível com o formato esperado pelo ``MeteoChunker``,
        incluindo campos extras do Open-Meteo (weather_code, etc).

        Args:
            city: Nome da cidade.
            days_back: Dias retroativos.

        Returns:
            Lista de sumários diários.
        """
        data = self.get_weather(city, days_back)
        if not data or "daily" not in data:
            return []

        daily = data["daily"]
        times: list[str] = daily.get("time", [])

        summaries: list[dict[str, Any]] = []
        for i, date_str in enumerate(times):
            avg_humidity = self._calc_daily_avg_humidity(data, date_str)
            obs_count = self._count_hourly_for_date(data, date_str)
            wmo_code = _safe_index(daily.get("weather_code"), i)

            summaries.append(
                {
                    "city": city,
                    "station_code": "Open-Meteo",
                    "date": date_str,
                    "total_rain_mm": _safe_index(daily.get("precipitation_sum"), i),
                    "max_temp_c": _safe_index(daily.get("temperature_2m_max"), i),
                    "min_temp_c": _safe_index(daily.get("temperature_2m_min"), i),
                    "avg_humidity_pct": avg_humidity,
                    "observation_count": obs_count,
                    "weather_code": wmo_code,
                    "weather_description": wmo_to_text(wmo_code),
                    "wind_max_kmh": _safe_index(daily.get("wind_speed_10m_max"), i),
                    "precipitation_hours": _safe_index(daily.get("precipitation_hours"), i),
                }
            )

        return summaries

    def get_observations(
        self,
        city: str,
        days_back: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna observações horárias normalizadas para o formato MeteoRAG.

        Converte vento de km/h para m/s para compatibilidade com
        o chunker (que espera m/s).

        Args:
            city: Nome da cidade.
            days_back: Dias retroativos.

        Returns:
            Lista de observações horárias.
        """
        data = self.get_weather(city, days_back)
        if not data or "hourly" not in data:
            return []

        hourly = data["hourly"]
        times: list[str] = hourly.get("time", [])

        observations: list[dict[str, Any]] = []
        for i, timestamp in enumerate(times):
            # Parse "2026-03-07T15:00" → date + time
            date_str = timestamp[:10]
            time_str = timestamp[11:16] if len(timestamp) >= 16 else "00:00"

            wind_kmh = _safe_index(hourly.get("wind_speed_10m"), i)
            wind_ms = round(wind_kmh / 3.6, 1) if wind_kmh is not None else None

            observations.append(
                {
                    "station_code": "Open-Meteo",
                    "date": date_str,
                    "time": time_str,
                    "rain_mm": _safe_index(hourly.get("precipitation"), i),
                    "temp_c": _safe_index(hourly.get("temperature_2m"), i),
                    "temp_max_c": None,
                    "temp_min_c": None,
                    "humidity_pct": _safe_index(hourly.get("relative_humidity_2m"), i),
                    "wind_speed_ms": wind_ms,
                    "wind_dir_deg": _safe_index(hourly.get("wind_direction_10m"), i),
                    "pressure_hpa": _safe_index(hourly.get("surface_pressure"), i),
                    "weather_code": _safe_index(hourly.get("weather_code"), i),
                }
            )

        return observations

    def get_current(self, city: str) -> dict[str, Any] | None:
        """Retorna condições atuais para uma cidade.

        Args:
            city: Nome da cidade.

        Returns:
            Dicionário com condições atuais ou ``None``.
        """
        data = self.get_weather(city, days_back=0)
        if not data or "current" not in data:
            return None

        current = data["current"]
        wind_kmh = current.get("wind_speed_10m")
        wind_ms = round(wind_kmh / 3.6, 1) if wind_kmh is not None else None
        wmo_code = current.get("weather_code")

        return {
            "city": city,
            "time": current.get("time", ""),
            "rain_mm": current.get("precipitation"),
            "temp_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_speed_ms": wind_ms,
            "pressure_hpa": current.get("surface_pressure"),
            "weather_code": wmo_code,
            "weather_description": wmo_to_text(wmo_code),
        }

    # ── Helpers ──────────────────────────────────────────

    @staticmethod
    def _calc_daily_avg_humidity(
        data: dict[str, Any],
        target_date: str,
    ) -> float | None:
        """Calcula umidade média diária a partir de dados horários.

        Args:
            data: Resposta completa da API Open-Meteo.
            target_date: Data alvo no formato ``YYYY-MM-DD``.

        Returns:
            Umidade média ou ``None``.
        """
        hourly = data.get("hourly", {})
        times: list[str] = hourly.get("time", [])
        humidity: list[float | None] = hourly.get("relative_humidity_2m", [])

        values: list[float] = []
        for i, ts in enumerate(times):
            if ts[:10] == target_date and i < len(humidity) and humidity[i] is not None:
                values.append(float(humidity[i]))  # type: ignore[arg-type]

        return round(sum(values) / len(values), 1) if values else None

    @staticmethod
    def _count_hourly_for_date(
        data: dict[str, Any],
        target_date: str,
    ) -> int:
        """Conta observações horárias para uma data específica.

        Args:
            data: Resposta completa da API Open-Meteo.
            target_date: Data alvo no formato ``YYYY-MM-DD``.

        Returns:
            Número de observações horárias.
        """
        times: list[str] = data.get("hourly", {}).get("time", [])
        return sum(1 for ts in times if ts[:10] == target_date)
