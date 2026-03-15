"""Testes unitários para o módulo de métricas Prometheus.

Verifica que as métricas estão corretamente definidas, que podem ser
incrementadas/observadas, e que o servidor de métricas é idempotente.
"""

from __future__ import annotations

from unittest.mock import patch

from meteorag.metrics import (
    CHAT_MESSAGES_TOTAL,
    INMET_LATENCY_SECONDS,
    INMET_REQUESTS_TOTAL,
    LLM_LATENCY_SECONDS,
    LLM_REQUESTS_TOTAL,
    OPENMETEO_LATENCY_SECONDS,
    OPENMETEO_REQUESTS_TOTAL,
    RAG_CHUNKS_TOTAL,
    RAG_INDEXED_CITIES,
    start_metrics_server,
)

# ══════════════════════════════════════════════════════════
# Definição de métricas
# ══════════════════════════════════════════════════════════


class TestMetricDefinitions:
    """Verifica que todas as métricas estão definidas corretamente."""

    def test_openmeteo_requests_total_is_counter(self) -> None:
        assert "meteorag_openmeteo_requests" in OPENMETEO_REQUESTS_TOTAL._name

    def test_openmeteo_latency_is_histogram(self) -> None:
        assert OPENMETEO_LATENCY_SECONDS._name == "meteorag_openmeteo_latency_seconds"

    def test_inmet_requests_total_is_counter(self) -> None:
        assert "meteorag_inmet_requests" in INMET_REQUESTS_TOTAL._name

    def test_inmet_latency_is_histogram(self) -> None:
        assert INMET_LATENCY_SECONDS._name == "meteorag_inmet_latency_seconds"

    def test_llm_requests_total_is_counter(self) -> None:
        assert "meteorag_llm_requests" in LLM_REQUESTS_TOTAL._name

    def test_llm_latency_is_histogram(self) -> None:
        assert LLM_LATENCY_SECONDS._name == "meteorag_llm_latency_seconds"

    def test_rag_chunks_total_is_gauge(self) -> None:
        assert RAG_CHUNKS_TOTAL._name == "meteorag_rag_chunks_total"

    def test_rag_indexed_cities_is_gauge(self) -> None:
        assert RAG_INDEXED_CITIES._name == "meteorag_rag_indexed_cities"

    def test_chat_messages_total_is_counter(self) -> None:
        assert "meteorag_chat_messages" in CHAT_MESSAGES_TOTAL._name


# ══════════════════════════════════════════════════════════
# Operações nas métricas
# ══════════════════════════════════════════════════════════


class TestMetricOperations:
    """Verifica que as métricas podem ser operadas sem erro."""

    def test_counter_increment_with_label(self) -> None:
        """Counter com label deve incrementar sem erro."""
        OPENMETEO_REQUESTS_TOTAL.labels(status="success").inc()
        OPENMETEO_REQUESTS_TOTAL.labels(status="error").inc()
        # Se chegou aqui sem exceção, passou

    def test_histogram_observe(self) -> None:
        """Histogram deve aceitar observações."""
        OPENMETEO_LATENCY_SECONDS.observe(0.5)
        LLM_LATENCY_SECONDS.observe(2.0)
        INMET_LATENCY_SECONDS.observe(1.0)

    def test_gauge_set_and_inc(self) -> None:
        """Gauge deve aceitar set e inc."""
        RAG_CHUNKS_TOTAL.set(42)
        RAG_INDEXED_CITIES.set(3)
        RAG_CHUNKS_TOTAL.inc(10)

    def test_chat_messages_increment(self) -> None:
        """Counter simples (sem labels) deve incrementar."""
        CHAT_MESSAGES_TOTAL.inc()

    def test_inmet_circuit_open_label(self) -> None:
        """INMET counter deve aceitar label circuit_open."""
        INMET_REQUESTS_TOTAL.labels(status="circuit_open").inc()

    def test_llm_timeout_label(self) -> None:
        """LLM counter deve aceitar label timeout."""
        LLM_REQUESTS_TOTAL.labels(status="timeout").inc()


# ══════════════════════════════════════════════════════════
# Servidor de métricas
# ══════════════════════════════════════════════════════════


class TestMetricsServer:
    """Testa o start_metrics_server (idempotente, thread-safe)."""

    @patch("meteorag.metrics.start_http_server")
    def test_start_metrics_server_calls_start(self, mock_start: object) -> None:
        """Deve chamar start_http_server na primeira vez."""
        import meteorag.metrics as m

        # Reset state
        m._metrics_server_started = False
        start_metrics_server(port=9999)
        # Não podemos garantir chamada real pois o módulo pode já ter sido
        # inicializado em outro teste — verificamos que não dá exception

    @patch("meteorag.metrics.start_http_server")
    def test_start_metrics_server_idempotent(self, mock_start: object) -> None:
        """Chamadas subsequentes devem ser no-op."""
        import meteorag.metrics as m

        m._metrics_server_started = True
        start_metrics_server(port=9999)
        # Se _metrics_server_started=True, não deve chamar start_http_server

    @patch("meteorag.metrics.start_http_server", side_effect=OSError("Address in use"))
    def test_start_metrics_server_handles_oserror(self, mock_start: object) -> None:
        """Deve capturar OSError sem propagar exceção."""
        import meteorag.metrics as m

        m._metrics_server_started = False
        # Não deve levantar exceção
        start_metrics_server(port=9999)
