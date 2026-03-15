"""Configuração centralizada do MeteoRAG via variáveis de ambiente.

Usa pydantic-settings para carregar, validar e tipar todas as configurações
do projeto a partir de variáveis de ambiente com prefixo METEORAG_.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais do MeteoRAG.

    Todas as variáveis de ambiente devem ter o prefixo ``METEORAG_``.
    Exemplo: ``METEORAG_ANTHROPIC_API_KEY`` → ``anthropic_api_key``.
    """

    model_config = SettingsConfigDict(
        env_prefix="METEORAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────
    anthropic_api_key: str = Field(
        default="",
        description="Chave da API Anthropic (obrigatório para LLM).",
    )
    anthropic_base_url: str = Field(
        default="",
        description="URL base opcional (ex: proxy Databricks).",
    )
    llm_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description="Modelo LLM padrão (Anthropic Claude Haiku).",
    )
    llm_max_tokens: int = Field(
        default=8192,
        ge=1,
        le=16384,
        description="Número máximo de tokens na resposta do LLM.",
    )
    llm_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout em segundos para chamadas ao LLM.",
    )

    # ── INMET ────────────────────────────────────────────
    inmet_base_url: str = Field(
        default="https://apitempo.inmet.gov.br",
        description="URL base da API pública do INMET.",
    )
    inmet_cache_ttl_seconds: int = Field(
        default=1800,
        ge=60,
        description="TTL do cache em memória para dados INMET (segundos).",
    )
    inmet_retry_max: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Número máximo de tentativas em caso de erro HTTP.",
    )
    inmet_timeout_seconds: int = Field(
        default=20,
        ge=5,
        le=60,
        description="Timeout em segundos para requisições à API INMET.",
    )
    default_days_back: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Número de dias retroativos para buscar dados.",
    )

    # ── Open-Meteo ───────────────────────────────────────
    openmeteo_timeout_seconds: int = Field(
        default=20,
        ge=5,
        le=60,
        description="Timeout em segundos para requisições à API Open-Meteo.",
    )

    # ── RAG ──────────────────────────────────────────────
    rag_top_k: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Número de chunks retornados pelo retriever.",
    )
    rag_max_chunk_size: int = Field(
        default=512,
        ge=100,
        le=2048,
        description="Tamanho máximo de cada chunk em caracteres.",
    )
    rag_max_hourly_chunks: int = Field(
        default=96,
        ge=1,
        description="Limite de chunks horários por indexação.",
    )

    # ── APP ──────────────────────────────────────────────
    app_port: int = Field(
        default=8501,
        ge=1024,
        le=65535,
        description="Porta do servidor Streamlit.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Nível de logging da aplicação.",
    )
    environment: Literal["development", "production"] = Field(
        default="development",
        description="Ambiente de execução.",
    )


# Instância singleton — importar em qualquer módulo:
#   from meteorag.config import settings
settings = Settings()
