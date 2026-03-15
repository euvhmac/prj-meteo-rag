"""Testes unitários para o circuit breaker do INMET client.

Verifica os estados (closed, open, half-open), transições
e o comportamento de cooldown.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import requests

from meteorag.api.inmet_client import (
    _CB_COOLDOWN_SECONDS,
    _CB_FAILURE_THRESHOLD,
    INMETClient,
    _CircuitBreaker,
)
from meteorag.config import Settings

# ══════════════════════════════════════════════════════════
# _CircuitBreaker — estados
# ══════════════════════════════════════════════════════════


class TestCircuitBreakerStates:
    """Testa transições de estado do circuit breaker."""

    def test_initial_state_is_closed(self) -> None:
        cb = _CircuitBreaker()
        assert cb.state == "closed"
        assert not cb.is_open

    def test_single_failure_stays_closed(self) -> None:
        cb = _CircuitBreaker()
        cb.record_failure()
        assert cb.state == "closed"

    def test_threshold_failures_opens_circuit(self) -> None:
        cb = _CircuitBreaker()
        for _ in range(_CB_FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open

    def test_success_resets_to_closed(self) -> None:
        cb = _CircuitBreaker()
        for _ in range(_CB_FAILURE_THRESHOLD - 1):
            cb.record_failure()
        cb.record_success()
        assert cb.state == "closed"
        assert not cb.is_open

    def test_success_after_open_closes_circuit(self) -> None:
        cb = _CircuitBreaker()
        for _ in range(_CB_FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.is_open
        # Simula cooldown expirado
        cb._last_failure_time = time.monotonic() - _CB_COOLDOWN_SECONDS - 1
        assert cb.state == "half-open"
        cb.record_success()
        assert cb.state == "closed"

    def test_reset_clears_all(self) -> None:
        cb = _CircuitBreaker()
        for _ in range(_CB_FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.is_open
        cb.reset()
        assert cb.state == "closed"
        assert not cb.is_open

    def test_half_open_after_cooldown(self) -> None:
        cb = _CircuitBreaker()
        for _ in range(_CB_FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.state == "open"
        # Simula passagem do tempo de cooldown
        cb._last_failure_time = time.monotonic() - _CB_COOLDOWN_SECONDS - 1
        assert cb.state == "half-open"


class TestCircuitBreakerThreshold:
    """Testa o limiar de falhas."""

    def test_exactly_threshold_minus_one_stays_closed(self) -> None:
        cb = _CircuitBreaker()
        for _ in range(_CB_FAILURE_THRESHOLD - 1):
            cb.record_failure()
        assert cb.state == "closed"

    def test_exactly_threshold_opens(self) -> None:
        cb = _CircuitBreaker()
        for _ in range(_CB_FAILURE_THRESHOLD):
            cb.record_failure()
        assert cb.state == "open"

    def test_more_than_threshold_stays_open(self) -> None:
        cb = _CircuitBreaker()
        for _ in range(_CB_FAILURE_THRESHOLD + 5):
            cb.record_failure()
        assert cb.state == "open"

    def test_failure_threshold_is_5(self) -> None:
        """O limiar padrão deve ser 5 conforme spec."""
        assert _CB_FAILURE_THRESHOLD == 5

    def test_cooldown_is_300_seconds(self) -> None:
        """O cooldown padrão deve ser 300s (5min) conforme spec."""
        assert _CB_COOLDOWN_SECONDS == 300


# ══════════════════════════════════════════════════════════
# INMETClient com circuit breaker
# ══════════════════════════════════════════════════════════


class TestINMETClientCircuitBreaker:
    """Testa a integração do circuit breaker no INMETClient."""

    def setup_method(self) -> None:
        """Reset circuit breaker entre testes."""
        INMETClient._circuit_breaker.reset()

    def test_client_exposes_circuit_breaker_state(self) -> None:
        settings = Settings(inmet_base_url="http://fake-inmet")
        client = INMETClient(settings)
        assert client.circuit_breaker_state == "closed"

    @patch("meteorag.api.inmet_client.requests.Session")
    def test_circuit_open_skips_request(self, mock_session_cls: MagicMock) -> None:
        """Com circuit aberto, não deve fazer requisição HTTP."""
        settings = Settings(inmet_base_url="http://fake-inmet")
        client = INMETClient(settings)

        # Força circuit breaker aberto
        for _ in range(_CB_FAILURE_THRESHOLD):
            client._circuit_breaker.record_failure()

        result = client._request("/test")
        assert result == []

        # Não deve ter feito chamada HTTP
        mock_session_cls.return_value.get.assert_not_called()

    @patch("meteorag.api.inmet_client.requests.Session")
    def test_circuit_open_returns_expired_cache(self, mock_session_cls: MagicMock) -> None:
        """Com circuit aberto e cache expirado, deve retornar cache."""
        from meteorag.api.inmet_client import _CacheEntry

        settings = Settings(inmet_base_url="http://fake-inmet")
        client = INMETClient(settings)

        # Popula cache com dados expirados
        url = "http://fake-inmet/test"
        expired_entry = _CacheEntry(data=[{"cached": True}], ttl_seconds=0)
        expired_entry.expires_at = 0  # Expirado
        client._cache[url] = expired_entry

        # Força circuit breaker aberto
        for _ in range(_CB_FAILURE_THRESHOLD):
            client._circuit_breaker.record_failure()

        result = client._request("/test")
        assert result == [{"cached": True}]

    @patch("meteorag.api.inmet_client.requests.Session")
    def test_successful_request_records_success(self, mock_session_cls: MagicMock) -> None:
        """Requisição bem-sucedida deve chamar record_success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"data": "ok"}]
        mock_response.raise_for_status.return_value = None
        mock_session_cls.return_value.get.return_value = mock_response

        settings = Settings(inmet_base_url="http://fake-inmet")
        client = INMETClient(settings)

        # Registra algumas falhas (mas menos que threshold)
        client._circuit_breaker.record_failure()
        client._circuit_breaker.record_failure()

        result = client._request("/test")
        assert result == [{"data": "ok"}]
        assert client.circuit_breaker_state == "closed"

    @patch("meteorag.api.inmet_client.requests.Session")
    @patch("meteorag.api.inmet_client.time.sleep")
    def test_all_retries_fail_records_failure(
        self, mock_sleep: MagicMock, mock_session_cls: MagicMock
    ) -> None:
        """Se todas as tentativas falharem, deve registrar falha no circuit breaker."""
        mock_session_cls.return_value.get.side_effect = requests.exceptions.Timeout("timeout")

        settings = Settings(
            inmet_base_url="http://fake-inmet",
            inmet_retry_max=2,
        )
        client = INMETClient(settings)
        client._circuit_breaker.reset()

        result = client._request("/test")
        assert result == []

    @patch("meteorag.api.inmet_client.requests.Session")
    @patch("meteorag.api.inmet_client.time.sleep")
    def test_fallback_returns_expired_cache_on_failure(
        self, mock_sleep: MagicMock, mock_session_cls: MagicMock
    ) -> None:
        """Se todas tentativas falharem e houver cache expirado, deve retornar cache."""
        from meteorag.api.inmet_client import _CacheEntry

        mock_session_cls.return_value.get.side_effect = requests.exceptions.Timeout("timeout")

        settings = Settings(
            inmet_base_url="http://fake-inmet",
            inmet_retry_max=1,
        )
        client = INMETClient(settings)

        # Popula cache expirado
        url = "http://fake-inmet/test"
        expired_entry = _CacheEntry(data=[{"fallback": True}], ttl_seconds=0)
        expired_entry.expires_at = 0
        client._cache[url] = expired_entry

        result = client._request("/test")
        assert result == [{"fallback": True}]
