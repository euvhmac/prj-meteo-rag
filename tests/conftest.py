"""Fixtures globais para testes do MeteoRAG.

Contém dados mock realistas da API INMET e Open-Meteo para testes unitários,
sem necessidade de conexão HTTP real.
"""

from __future__ import annotations

from typing import Any

import pytest

# ══════════════════════════════════════════════════════════
# Estações
# ══════════════════════════════════════════════════════════


@pytest.fixture()
def sample_stations() -> list[dict[str, Any]]:
    """Lista parcial de estações automáticas INMET (formato real da API)."""
    return [
        {
            "CD_ESTACAO": "A518",
            "DC_NOME": "JUIZ DE FORA",
            "SG_ESTADO": "MG",
            "VL_LATITUDE": "-21.7666",
            "VL_LONGITUDE": "-43.3641",
            "VL_ALTITUDE": "940.0",
            "DT_INICIO_OPERACAO": "2006-12-14",
            "CD_SITUACAO": "Operante",
            "TP_ESTACAO": "Automatica",
        },
        {
            "CD_ESTACAO": "A519",
            "DC_NOME": "BARBACENA",
            "SG_ESTADO": "MG",
            "VL_LATITUDE": "-21.2258",
            "VL_LONGITUDE": "-43.7736",
            "VL_ALTITUDE": "1126.0",
            "DT_INICIO_OPERACAO": "2006-08-01",
            "CD_SITUACAO": "Operante",
            "TP_ESTACAO": "Automatica",
        },
        {
            "CD_ESTACAO": "A520",
            "DC_NOME": "VICOSA",
            "SG_ESTADO": "MG",
            "VL_LATITUDE": "-20.7652",
            "VL_LONGITUDE": "-42.8702",
            "VL_ALTITUDE": "712.2",
            "DT_INICIO_OPERACAO": "2006-09-20",
            "CD_SITUACAO": "Operante",
            "TP_ESTACAO": "Automatica",
        },
        {
            "CD_ESTACAO": "A521",
            "DC_NOME": "BELO HORIZONTE",
            "SG_ESTADO": "MG",
            "VL_LATITUDE": "-19.8833",
            "VL_LONGITUDE": "-43.9666",
            "VL_ALTITUDE": "869.0",
            "DT_INICIO_OPERACAO": "2000-05-07",
            "CD_SITUACAO": "Operante",
            "TP_ESTACAO": "Automatica",
        },
        {
            "CD_ESTACAO": "A001",
            "DC_NOME": "BRASILIA",
            "SG_ESTADO": "DF",
            "VL_LATITUDE": "-15.7891",
            "VL_LONGITUDE": "-47.9258",
            "VL_ALTITUDE": "1160.0",
            "DT_INICIO_OPERACAO": "2000-05-07",
            "CD_SITUACAO": "Operante",
            "TP_ESTACAO": "Automatica",
        },
    ]


# ══════════════════════════════════════════════════════════
# Observações horárias
# ══════════════════════════════════════════════════════════


@pytest.fixture()
def sample_hourly_observations() -> list[dict[str, Any]]:
    """Observações horárias da estação A518 (Juiz de Fora) — formato real da API."""
    return [
        {
            "CD_ESTACAO": "A518",
            "DT_MEDICAO": "2024-01-15",
            "HR_MEDICAO": "1200 UTC",
            "CHUVA": "2.4",
            "TEM_INS": "22.5",
            "TEM_MAX": "23.1",
            "TEM_MIN": "21.8",
            "UMD_INS": "78.0",
            "VEN_VEL": "3.2",
            "VEN_DIR": "180.0",
            "PRE_INS": "912.5",
            "RAD_GLO": "1850.0",
        },
        {
            "CD_ESTACAO": "A518",
            "DT_MEDICAO": "2024-01-15",
            "HR_MEDICAO": "1300 UTC",
            "CHUVA": "0.0",
            "TEM_INS": "24.1",
            "TEM_MAX": "24.5",
            "TEM_MIN": "22.5",
            "UMD_INS": "72.0",
            "VEN_VEL": "4.1",
            "VEN_DIR": "200.0",
            "PRE_INS": "911.8",
            "RAD_GLO": "2100.0",
        },
        {
            "CD_ESTACAO": "A518",
            "DT_MEDICAO": "2024-01-15",
            "HR_MEDICAO": "1400 UTC",
            "CHUVA": "15.6",
            "TEM_INS": "20.3",
            "TEM_MAX": "24.5",
            "TEM_MIN": "20.1",
            "UMD_INS": "92.0",
            "VEN_VEL": "6.5",
            "VEN_DIR": "270.0",
            "PRE_INS": "910.2",
            "RAD_GLO": "450.0",
        },
        {
            "CD_ESTACAO": "A518",
            "DT_MEDICAO": "2024-01-16",
            "HR_MEDICAO": "1200 UTC",
            "CHUVA": "0.0",
            "TEM_INS": "26.8",
            "TEM_MAX": "27.2",
            "TEM_MIN": "25.5",
            "UMD_INS": "65.0",
            "VEN_VEL": "2.8",
            "VEN_DIR": "150.0",
            "PRE_INS": "913.0",
            "RAD_GLO": "2500.0",
        },
    ]


@pytest.fixture()
def sample_observations_with_nulls() -> list[dict[str, Any]]:
    """Observações com valores inválidos/nulos (edge cases da API INMET)."""
    return [
        {
            "CD_ESTACAO": "A518",
            "DT_MEDICAO": "2024-01-17",
            "HR_MEDICAO": "0000 UTC",
            "CHUVA": None,
            "TEM_INS": "-9999",
            "TEM_MAX": "9999",
            "TEM_MIN": "",
            "UMD_INS": None,
            "VEN_VEL": "0.0",
            "VEN_DIR": None,
            "PRE_INS": "-9999",
            "RAD_GLO": "",
        },
        {
            "CD_ESTACAO": "A518",
            "DT_MEDICAO": "2024-01-17",
            "HR_MEDICAO": "0100 UTC",
            "CHUVA": "9999",
            "TEM_INS": None,
            "TEM_MAX": None,
            "TEM_MIN": None,
            "UMD_INS": "9999",
            "VEN_VEL": "-9999",
            "VEN_DIR": "9999",
            "PRE_INS": None,
            "RAD_GLO": None,
        },
    ]


# ══════════════════════════════════════════════════════════
# Alertas
# ══════════════════════════════════════════════════════════


@pytest.fixture()
def sample_alerts() -> list[dict[str, Any]]:
    """Alertas meteorológicos para MG — formato real da API INMET."""
    return [
        {
            "id_alerta": "1234",
            "descricao": "Chuvas intensas com acumulado de 50 a 100mm/dia",
            "severidade": "Perigo",
            "inicio": "2024-01-15T10:00:00",
            "fim": "2024-01-16T10:00:00",
            "evento": "Chuvas Intensas",
            "municipios": "Juiz de Fora, Ubá, Viçosa, Muriaé, Barbacena",
            "estado": "MG",
        },
        {
            "id_alerta": "1235",
            "descricao": "Tempestades com ventos de 60 a 100km/h e granizo",
            "severidade": "Grande Perigo",
            "inicio": "2024-01-15T14:00:00",
            "fim": "2024-01-15T23:00:00",
            "evento": "Tempestade",
            "municipios": "Juiz de Fora, Santos Dumont",
            "estado": "MG",
        },
    ]


@pytest.fixture()
def empty_alerts() -> list[dict[str, Any]]:
    """Resposta quando não há alertas (HTTP 204 convertido para lista vazia)."""
    return []


# ══════════════════════════════════════════════════════════
# Daily Summaries (dados já processados)
# ══════════════════════════════════════════════════════════


@pytest.fixture()
def sample_daily_summaries() -> list[dict[str, Any]]:
    """Sumários diários já processados (output esperado do chunker)."""
    return [
        {
            "city": "Juiz de Fora",
            "station_code": "A518",
            "date": "2024-01-15",
            "total_rain_mm": 18.0,
            "max_temp_c": 24.5,
            "min_temp_c": 20.1,
            "avg_humidity_pct": 80.67,
            "observation_count": 3,
        },
        {
            "city": "Juiz de Fora",
            "station_code": "A518",
            "date": "2024-01-16",
            "total_rain_mm": 0.0,
            "max_temp_c": 27.2,
            "min_temp_c": 25.5,
            "avg_humidity_pct": 65.0,
            "observation_count": 1,
        },
    ]


# ══════════════════════════════════════════════════════════
# Chunks RAG
# ══════════════════════════════════════════════════════════


@pytest.fixture()
def sample_chunks() -> list[dict[str, Any]]:
    """Chunks de texto já construídos para o retriever."""
    return [
        {
            "text": (
                "Resumo diário — Juiz de Fora (A518) — 15/01/2024: "
                "Chuva total de 18.0mm (chuva moderada). "
                "Temperatura máxima de 24.5°C e mínima de 20.1°C. "
                "Umidade média de 80.7%. "
                "Baseado em 3 observações."
            ),
            "metadata": {
                "city": "Juiz de Fora",
                "date": "2024-01-15",
                "type": "daily",
            },
        },
        {
            "text": (
                "Resumo diário — Juiz de Fora (A518) — 16/01/2024: "
                "Sem chuva registrada. "
                "Temperatura máxima de 27.2°C e mínima de 25.5°C. "
                "Umidade média de 65.0%. "
                "Baseado em 1 observação."
            ),
            "metadata": {
                "city": "Juiz de Fora",
                "date": "2024-01-16",
                "type": "daily",
            },
        },
        {
            "text": (
                "Observação horária — Juiz de Fora (A518) — 15/01/2024 14:00 UTC: "
                "Chuva de 15.6mm na última hora. "
                "Temperatura 20.3°C, umidade 92.0%. "
                "Vento de 6.5 m/s a 270°."
            ),
            "metadata": {
                "city": "Juiz de Fora",
                "date": "2024-01-15",
                "type": "hourly",
            },
        },
        {
            "text": (
                "ALERTA METEOROLÓGICO — MG — Perigo: Chuvas Intensas. "
                "Vigência: 15/01/2024 10:00 a 16/01/2024 10:00. "
                "Chuvas intensas com acumulado de 50 a 100mm/dia. "
                "Municípios: Juiz de Fora, Ubá, Viçosa, Muriaé, Barbacena."
            ),
            "metadata": {
                "city": "MG",
                "date": "2024-01-15",
                "type": "alert",
            },
        },
        {
            "text": (
                "Contexto semanal — Juiz de Fora (A518) — 09/01 a 16/01/2024: "
                "Total de chuva na semana: 18.0mm. "
                "Dias com chuva: 1 de 2 dias com dados. "
                "Dia mais chuvoso: 15/01/2024 com 18.0mm. "
                "Temperatura mais alta: 27.2°C em 16/01/2024."
            ),
            "metadata": {
                "city": "Juiz de Fora",
                "date": "2024-01-16",
                "type": "context",
            },
        },
    ]


# ══════════════════════════════════════════════════════════
# Open-Meteo API Response
# ══════════════════════════════════════════════════════════


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
        "current": {
            "time": "2024-01-18T14:00",
            "precipitation": 0.0,
            "temperature_2m": 25.3,
            "relative_humidity_2m": 68,
            "wind_speed_10m": 12.5,
            "weather_code": 2,
            "surface_pressure": 912.0,
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
