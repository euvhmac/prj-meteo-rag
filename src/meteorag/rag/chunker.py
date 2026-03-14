"""Conversão de dados meteorológicos INMET em chunks de texto para RAG.

Gera 4 tipos de chunk: daily, hourly, alert e context.
Cada chunk é um dicionário ``{"text": str, "metadata": dict}`` com no
máximo 512 caracteres de texto.
"""

from __future__ import annotations

import logging
from typing import Any

from meteorag.config import Settings

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Helpers de formatação
# ═══════════════════════════════════════════════════════════


def _fmt_rain(rain_mm: float | None) -> str:
    """Descreve a chuva em texto legível.

    Args:
        rain_mm: Total de chuva em milímetros (ou ``None``).

    Returns:
        Descrição textual da chuva.
    """
    if rain_mm is None:
        return "Sem dados de chuva"
    if rain_mm == 0.0:
        return "Sem chuva registrada"
    if rain_mm < 5.0:
        return f"Chuva fraca de {rain_mm}mm"
    if rain_mm < 25.0:
        return f"Chuva moderada de {rain_mm}mm"
    if rain_mm < 50.0:
        return f"Chuva forte de {rain_mm}mm"
    return f"Chuva muito forte de {rain_mm}mm"


def _fmt_date_br(date_str: str) -> str:
    """Converte ``YYYY-MM-DD`` para ``DD/MM/YYYY``.

    Args:
        date_str: Data no formato ISO.

    Returns:
        Data formatada em padrão brasileiro.
    """
    try:
        parts = date_str.split("-")
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except (IndexError, AttributeError):
        return date_str


def _safe_fmt(value: float | None, unit: str, decimals: int = 1) -> str:
    """Formata valor numérico com unidade, ou retorna 'sem dados'.

    Args:
        value: Valor numérico ou ``None``.
        unit: Unidade de medida (ex: ``°C``, ``%``).
        decimals: Casas decimais.

    Returns:
        String formatada.
    """
    if value is None:
        return "sem dados"
    return f"{value:.{decimals}f}{unit}"


# ═══════════════════════════════════════════════════════════
# Funções de chunking
# ═══════════════════════════════════════════════════════════


def chunk_daily_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Gera um chunk de texto a partir de um sumário diário.

    Args:
        summary: Sumário diário (output de ``get_daily_summary``).

    Returns:
        Chunk com ``text`` e ``metadata``.
    """
    city = summary.get("city", "Desconhecida")
    code = summary.get("station_code", "?")
    date_str = summary.get("date", "?")
    date_br = _fmt_date_br(date_str)

    rain_desc = _fmt_rain(summary.get("total_rain_mm"))
    max_temp = _safe_fmt(summary.get("max_temp_c"), "°C")
    min_temp = _safe_fmt(summary.get("min_temp_c"), "°C")
    humidity = _safe_fmt(summary.get("avg_humidity_pct"), "%")
    obs_count = summary.get("observation_count", 0)

    # Condição WMO (Open-Meteo) — opcional, ausente em dados INMET
    weather_desc = summary.get("weather_description", "")
    weather_part = f"Condição: {weather_desc}. " if weather_desc else ""

    text = (
        f"Resumo diário — {city} ({code}) — {date_br}: "
        f"{weather_part}"
        f"{rain_desc}. "
        f"Temperatura máxima de {max_temp} e mínima de {min_temp}. "
        f"Umidade média de {humidity}. "
        f"Baseado em {obs_count} observaç{'ão' if obs_count == 1 else 'ões'}."
    )

    return {
        "text": text[:512],
        "metadata": {
            "city": city,
            "date": date_str,
            "type": "daily",
        },
    }


def chunk_hourly_observation(obs: dict[str, Any], city: str) -> dict[str, Any]:
    """Gera um chunk de texto a partir de uma observação horária.

    Apenas observações com chuva > 0 ou temperatura notável são
    convertidas em chunk (filtro fica no chamador).

    Args:
        obs: Observação normalizada (output de ``parse_observation``).
        city: Nome da cidade.

    Returns:
        Chunk com ``text`` e ``metadata``.
    """
    code = obs.get("station_code", "?")
    date_str = obs.get("date", "?")
    time_str = obs.get("time", "?")
    date_br = _fmt_date_br(date_str)

    rain = obs.get("rain_mm")
    temp = obs.get("temp_c")
    humidity = obs.get("humidity_pct")
    wind = obs.get("wind_speed_ms")
    wind_dir = obs.get("wind_dir_deg")

    parts = [f"Observação horária — {city} ({code}) — {date_br} {time_str}:"]

    if rain is not None and rain > 0:
        parts.append(f"Chuva de {rain}mm na última hora.")
    elif rain is not None:
        parts.append("Sem chuva na última hora.")

    if temp is not None:
        parts.append(f"Temperatura {temp}°C")
        if humidity is not None:
            parts[-1] += f", umidade {humidity}%."
        else:
            parts[-1] += "."

    if wind is not None:
        wind_text = f"Vento de {wind} m/s"
        if wind_dir is not None:
            wind_text += f" a {wind_dir:.0f}°"
        wind_text += "."
        parts.append(wind_text)

    text = " ".join(parts)

    return {
        "text": text[:512],
        "metadata": {
            "city": city,
            "date": date_str,
            "type": "hourly",
        },
    }


def chunk_alert(alert: dict[str, Any]) -> dict[str, Any]:
    """Gera um chunk de texto a partir de um alerta meteorológico.

    Args:
        alert: Alerta no formato bruto da API ou normalizado.

    Returns:
        Chunk com ``text`` e ``metadata``.
    """
    # Suporta tanto formato bruto quanto normalizado
    state = alert.get("state", alert.get("estado", "MG"))
    severity = alert.get("severity", alert.get("severidade", ""))
    event = alert.get("event", alert.get("evento", ""))
    description = alert.get("description", alert.get("descricao", ""))
    cities = alert.get("cities", alert.get("municipios", ""))
    start = alert.get("start", alert.get("inicio", ""))
    end = alert.get("end", alert.get("fim", ""))

    # Formata datas de vigência
    start_fmt = _fmt_date_br(start[:10]) if len(start) >= 10 else start
    end_fmt = _fmt_date_br(end[:10]) if len(end) >= 10 else end
    start_time = start[11:16] if len(start) >= 16 else ""
    end_time = end[11:16] if len(end) >= 16 else ""

    vigencia = f"{start_fmt}"
    if start_time:
        vigencia += f" {start_time}"
    vigencia += f" a {end_fmt}"
    if end_time:
        vigencia += f" {end_time}"

    text = (
        f"ALERTA METEOROLÓGICO — {state} — {severity}: {event}. "
        f"Vigência: {vigencia}. "
        f"{description}. "
        f"Municípios: {cities}."
    )

    # Extrai data do alerta para metadata
    alert_date = start[:10] if len(start) >= 10 else ""

    return {
        "text": text[:512],
        "metadata": {
            "city": state,
            "date": alert_date,
            "type": "alert",
        },
    }


def chunk_weekly_context(
    daily_summaries: list[dict[str, Any]],
    city: str,
    station_code: str,
) -> dict[str, Any] | None:
    """Gera um chunk de contexto semanal a partir de sumários diários.

    Args:
        daily_summaries: Lista de sumários diários para uma cidade.
        city: Nome da cidade.
        station_code: Código da estação.

    Returns:
        Chunk de contexto ou ``None`` se não houver dados suficientes.
    """
    if not daily_summaries:
        return None

    sorted_summaries = sorted(daily_summaries, key=lambda s: s.get("date", ""))
    first_date = sorted_summaries[0].get("date", "?")
    last_date = sorted_summaries[-1].get("date", "?")

    # Calcula estatísticas semanais
    total_rain = 0.0
    rainy_days = 0
    max_rain_day = ""
    max_rain_val = 0.0
    max_temp = -999.0
    max_temp_date = ""

    for s in sorted_summaries:
        rain = s.get("total_rain_mm")
        if rain is not None and rain > 0:
            total_rain += rain
            rainy_days += 1
            if rain > max_rain_val:
                max_rain_val = rain
                max_rain_day = s.get("date", "?")

        temp = s.get("max_temp_c")
        if temp is not None and temp > max_temp:
            max_temp = temp
            max_temp_date = s.get("date", "?")

    total_days = len(sorted_summaries)
    first_br = _fmt_date_br(first_date)
    last_br = _fmt_date_br(last_date)

    parts = [
        f"Contexto semanal — {city} ({station_code}) — {first_br} a {last_br}:",
        f"Total de chuva na semana: {total_rain:.1f}mm.",
        f"Dias com chuva: {rainy_days} de {total_days} dias com dados.",
    ]

    if max_rain_day:
        parts.append(f"Dia mais chuvoso: {_fmt_date_br(max_rain_day)} com {max_rain_val}mm.")

    if max_temp > -999.0:
        parts.append(f"Temperatura mais alta: {max_temp}°C em {_fmt_date_br(max_temp_date)}.")

    text = " ".join(parts)

    return {
        "text": text[:512],
        "metadata": {
            "city": city,
            "date": last_date,
            "type": "context",
        },
    }


# ═══════════════════════════════════════════════════════════
# Classe orquestradora
# ═══════════════════════════════════════════════════════════


class MeteoChunker:
    """Converte dados meteorológicos brutos em chunks para o RAG.

    Coordena todos os tipos de chunking e respeita o limite de
    tamanho e quantidade configurados.

    Args:
        settings: Configurações do projeto (opcional).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self.max_chunk_size = self._settings.rag_max_chunk_size
        self.max_hourly_chunks = self._settings.rag_max_hourly_chunks

    def chunk_all(
        self,
        daily_summaries: list[dict[str, Any]],
        observations: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
        city: str,
        station_code: str,
    ) -> list[dict[str, Any]]:
        """Gera todos os chunks para uma cidade.

        Args:
            daily_summaries: Sumários diários.
            observations: Observações horárias normalizadas.
            alerts: Alertas meteorológicos.
            city: Nome da cidade.
            station_code: Código da estação.

        Returns:
            Lista de chunks ordenados por relevância (alertas primeiro,
            depois contexto, depois diários, depois horários).
        """
        chunks: list[dict[str, Any]] = []

        # 1. Alertas (máxima prioridade)
        for alert in alerts:
            chunk = chunk_alert(alert)
            chunks.append(chunk)

        # 2. Contexto semanal
        ctx = chunk_weekly_context(daily_summaries, city, station_code)
        if ctx is not None:
            chunks.append(ctx)

        # 3. Sumários diários
        for summary in daily_summaries:
            chunk = chunk_daily_summary(summary)
            chunks.append(chunk)

        # 4. Observações horárias (apenas com chuva > 0 ou condições notáveis)
        hourly_count = 0
        for obs in observations:
            if hourly_count >= self.max_hourly_chunks:
                break
            rain = obs.get("rain_mm")
            wind = obs.get("wind_speed_ms")
            # Filtra: só inclui se chuva > 0 ou vento > 10 m/s
            if (rain is not None and rain > 0) or (wind is not None and wind > 10.0):
                chunk = chunk_hourly_observation(obs, city)
                chunks.append(chunk)
                hourly_count += 1

        logger.info(
            "Chunker gerou %d chunks para %s (%s): %d alertas, %d diários, %d horários",
            len(chunks),
            city,
            station_code,
            len(alerts),
            len(daily_summaries),
            hourly_count,
        )

        return chunks
