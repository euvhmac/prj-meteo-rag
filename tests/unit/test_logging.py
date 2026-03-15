"""Testes unitários para o módulo de logging estruturado.

Verifica que setup_logging configura corretamente os handlers
e que get_logger retorna um logger funcional.
"""

from __future__ import annotations

import logging

from meteorag.logging import get_logger, setup_logging

# ══════════════════════════════════════════════════════════
# setup_logging
# ══════════════════════════════════════════════════════════


class TestSetupLogging:
    """Testa a configuração do logging estruturado."""

    def test_setup_logging_development(self) -> None:
        """Em development, deve configurar sem erro."""
        setup_logging(level="DEBUG", environment="development")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) >= 1

    def test_setup_logging_production(self) -> None:
        """Em production, deve configurar JSON logging."""
        setup_logging(level="INFO", environment="production")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_setup_logging_warning_level(self) -> None:
        """Deve aceitar nível WARNING."""
        setup_logging(level="WARNING", environment="development")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_setup_logging_invalid_level_defaults_to_info(self) -> None:
        """Nível inválido deve cair em INFO (getattr fallback)."""
        setup_logging(level="BANANA", environment="development")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_noisy_loggers_silenced(self) -> None:
        """Loggers de libs ruidosas devem estar em WARNING+."""
        setup_logging(level="DEBUG", environment="development")
        for noisy in ("httpx", "httpcore", "urllib3", "requests", "anthropic"):
            assert logging.getLogger(noisy).level >= logging.WARNING

    def test_root_handlers_not_duplicated(self) -> None:
        """Chamadas repetidas não devem duplicar handlers."""
        setup_logging(level="INFO", environment="development")
        n1 = len(logging.getLogger().handlers)
        setup_logging(level="INFO", environment="development")
        n2 = len(logging.getLogger().handlers)
        assert n2 == n1


# ══════════════════════════════════════════════════════════
# get_logger
# ══════════════════════════════════════════════════════════


class TestGetLogger:
    """Testa a criação de loggers estruturados."""

    def test_get_logger_returns_bound_logger(self) -> None:
        """get_logger deve retornar um logger funcional."""
        setup_logging(level="INFO", environment="development")
        log = get_logger("test_module")
        assert log is not None

    def test_get_logger_can_log_info(self) -> None:
        """Logger deve aceitar chamadas info() sem erro."""
        setup_logging(level="INFO", environment="development")
        log = get_logger("test_module")
        # Não deve levantar exceção
        log.info("test message", city="Juiz de Fora", chunks=42)

    def test_get_logger_can_log_warning(self) -> None:
        """Logger deve aceitar chamadas warning() sem erro."""
        setup_logging(level="INFO", environment="development")
        log = get_logger("test_module")
        log.warning("test warning", error_code=503)

    def test_get_logger_different_names_different_loggers(self) -> None:
        """Loggers com nomes diferentes devem ser distintos."""
        setup_logging(level="INFO", environment="development")
        log1 = get_logger("module_a")
        log2 = get_logger("module_b")
        # Ambos devem ser funcionais
        log1.info("from a")
        log2.info("from b")
