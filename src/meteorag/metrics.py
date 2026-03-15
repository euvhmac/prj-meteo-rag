"""Métricas Prometheus para o MeteoRAG.

Define counters, histograms e gauges usados para monitorar:
- Requisições à API Open-Meteo e INMET (success/error + latência)
- Requisições ao LLM (success/error + latência)
- Total de chunks indexados no RAG
- Mensagens de chat processadas

As métricas são exportadas via ``prometheus_client.start_http_server``
na porta 8502 (configurável).
"""

from __future__ import annotations

import logging
import threading

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Métricas — API (Open-Meteo + INMET)
# ═══════════════════════════════════════════════════════════

OPENMETEO_REQUESTS_TOTAL = Counter(
    "meteorag_openmeteo_requests_total",
    "Total de requisições à API Open-Meteo",
    ["status"],  # success | error
)

OPENMETEO_LATENCY_SECONDS = Histogram(
    "meteorag_openmeteo_latency_seconds",
    "Latência das requisições à API Open-Meteo",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

INMET_REQUESTS_TOTAL = Counter(
    "meteorag_inmet_requests_total",
    "Total de requisições à API INMET",
    ["status"],  # success | error
)

INMET_LATENCY_SECONDS = Histogram(
    "meteorag_inmet_latency_seconds",
    "Latência das requisições à API INMET",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0],
)

# ═══════════════════════════════════════════════════════════
# Métricas — LLM
# ═══════════════════════════════════════════════════════════

LLM_REQUESTS_TOTAL = Counter(
    "meteorag_llm_requests_total",
    "Total de requisições ao LLM",
    ["status"],  # success | error | timeout
)

LLM_LATENCY_SECONDS = Histogram(
    "meteorag_llm_latency_seconds",
    "Latência das requisições ao LLM",
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0],
)

# ═══════════════════════════════════════════════════════════
# Métricas — RAG
# ═══════════════════════════════════════════════════════════

RAG_CHUNKS_TOTAL = Gauge(
    "meteorag_rag_chunks_total",
    "Total de chunks indexados no RAG",
)

RAG_INDEXED_CITIES = Gauge(
    "meteorag_rag_indexed_cities",
    "Número de cidades indexadas no RAG",
)

# ═══════════════════════════════════════════════════════════
# Métricas — Chat
# ═══════════════════════════════════════════════════════════

CHAT_MESSAGES_TOTAL = Counter(
    "meteorag_chat_messages_total",
    "Total de mensagens de chat processadas",
)

# ═══════════════════════════════════════════════════════════
# Servidor de métricas
# ═══════════════════════════════════════════════════════════

_metrics_server_started = False
_metrics_lock = threading.Lock()


def start_metrics_server(port: int = 8502) -> None:
    """Inicia o servidor HTTP de métricas Prometheus.

    Thread-safe: ignora chamadas subsequentes se já estiver rodando.

    Args:
        port: Porta para o endpoint ``/metrics``.
    """
    global _metrics_server_started
    with _metrics_lock:
        if _metrics_server_started:
            return
        try:
            start_http_server(port)
            _metrics_server_started = True
            logger.info("Prometheus metrics server iniciado na porta %d", port)
        except OSError as exc:
            logger.warning("Não foi possível iniciar metrics server na porta %d: %s", port, exc)
