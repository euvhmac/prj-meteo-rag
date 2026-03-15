"""Logging estruturado com structlog para o MeteoRAG.

Configura logging JSON em produção e logging colorido em desenvolvimento.
Campos padrão em cada log: timestamp, level, module, message.

Uso:
    from meteorag.logging import setup_logging, get_logger
    setup_logging("INFO", "production")
    logger = get_logger(__name__)
    logger.info("mensagem", city="Juiz de Fora", chunks=42)
"""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(
    level: str = "INFO",
    environment: str = "development",
) -> None:
    """Configura logging estruturado para toda a aplicação.

    Em produção: JSON puro para parsing por Loki/Elasticsearch.
    Em desenvolvimento: output colorido legível no terminal.

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        environment: Ambiente de execução (development | production).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if environment == "production":
        # JSON logs para produção
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Logs coloridos para desenvolvimento
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configura root logger do stdlib
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Reduz verbosidade de libs terceiros
    for noisy in ("httpx", "httpcore", "urllib3", "requests", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado com bind automático do nome do módulo.

    Args:
        name: Nome do módulo (tipicamente ``__name__``).

    Returns:
        Logger estruturado pronto para uso.
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]
