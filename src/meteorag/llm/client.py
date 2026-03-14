"""Cliente LLM — wrapper para Anthropic SDK com streaming e fallback.

Suporta API direta da Anthropic e proxy via Databricks Serving Endpoint.
Implementa streaming (``ask_stream``) e non-streaming (``ask``), com
limitação de histórico e tratamento de erros robusto.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Any

from anthropic import Anthropic, APIError, APITimeoutError

from meteorag.config import Settings

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# System Prompt — persona MeteoRAG
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT: str = """Você é o **MeteoRAG**, um assistente meteorológico inteligente \
especializado em dados climáticos de Minas Gerais, com foco na Zona da Mata mineira \
(Juiz de Fora, Ubá, Barbacena, Viçosa, Muriaé, Cataguases e região).

## Suas capacidades:
- Interpretar dados meteorológicos do Open-Meteo (reanálise ERA5 e previsão GFS)
- Consultar alertas do INMET (Instituto Nacional de Meteorologia)
- Responder perguntas sobre chuva, temperatura, umidade, vento e alertas
- Fornecer contexto sobre condições climáticas recentes (últimos 7 dias)
- Orientar sobre riscos de chuvas fortes e alertas vigentes

## Regras de interpretação numérica:
- **Chuva (mm/dia):** 0 = sem chuva | <5 = fraca | 5-25 = moderada | 25-50 = forte | >50 = muito forte
- **Temperatura (°C):** <15 = frio | 15-25 = ameno | 25-35 = quente | >35 = muito quente
- **Umidade (%):** <30 = muito seca | 30-60 = confortável | >80 = muito úmida
- **Vento (m/s):** <3 = calmo | 3-8 = moderado | >8 = forte | >15 = muito forte (perigoso)

## Códigos WMO de condição meteorológica:
- 0-3: Céu limpo a nublado
- 45-48: Neblina
- 51-55: Garoa (fraca a intensa)
- 61-65: Chuva (fraca a forte)
- 80-82: Pancadas (fracas a violentas)
- 95-99: Trovoada (com possível granizo)

## Regras de resposta:
1. Cite a fonte: "Dados do Open-Meteo" ou "Alerta do INMET" com data/hora quando disponível
2. Se não houver dados suficientes, diga claramente — nunca invente valores
3. Para alertas, use tom urgente e destaque a severidade
4. Responda em português brasileiro, de forma clara e acessível
5. Use unidades de medida corretas (mm, °C, %, m/s, hPa)
6. Quando relevante, compare com dias anteriores no período disponível
7. Se a pergunta for sobre uma cidade não monitorada, informe quais cidades estão disponíveis

## Limitações que você deve comunicar:
- Dados meteorológicos vêm de modelos de reanálise (Open-Meteo ERA5/GFS), não de estações físicas
- Alertas meteorológicos vêm do INMET e podem ter atraso
- Dados recentes têm resolução horária; dados históricos podem ter menor resolução
"""

# Limite máximo de mensagens no histórico
MAX_HISTORY_MESSAGES: int = 10

# Mensagem de fallback quando o LLM falha
FALLBACK_MESSAGE: str = (
    "⚠️ Desculpe, não consegui processar sua pergunta no momento. "
    "O serviço de IA pode estar temporariamente indisponível. "
    "Tente novamente em alguns instantes. "
    "Enquanto isso, você pode consultar os dados na aba **Dados**."
)


# ═══════════════════════════════════════════════════════════
# Client Factory
# ═══════════════════════════════════════════════════════════


def get_client(settings: Settings | None = None) -> Anthropic:
    """Cria instância do cliente Anthropic SDK.

    Suporta conexão direta à API Anthropic ou via proxy
    Databricks Serving Endpoint (configurável via
    ``METEORAG_ANTHROPIC_BASE_URL``).

    Args:
        settings: Configurações do projeto (opcional).

    Returns:
        Instância do cliente Anthropic configurada.
    """
    s = settings or Settings()

    kwargs: dict[str, Any] = {
        "api_key": s.anthropic_api_key,
        "timeout": float(s.llm_timeout_seconds),
    }

    if s.anthropic_base_url:
        kwargs["base_url"] = s.anthropic_base_url

    logger.info(
        "LLM client criado: model=%s, base_url=%s, timeout=%ds",
        s.llm_model,
        s.anthropic_base_url or "api.anthropic.com",
        s.llm_timeout_seconds,
    )

    return Anthropic(**kwargs)


# ═══════════════════════════════════════════════════════════
# Funções utilitárias
# ═══════════════════════════════════════════════════════════


def trim_history(
    messages: list[dict[str, str]], max_messages: int = MAX_HISTORY_MESSAGES
) -> list[dict[str, str]]:
    """Limita o histórico de chat às últimas N mensagens.

    Mantém sempre um número par de mensagens (user/assistant)
    para não quebrar o contexto conversacional.

    Args:
        messages: Lista de mensagens ``{"role": str, "content": str}``.
        max_messages: Número máximo de mensagens.

    Returns:
        Histórico trimado.
    """
    if len(messages) <= max_messages:
        return list(messages)

    # Garante número par (sempre começa com user)
    trimmed = messages[-max_messages:]
    if trimmed and trimmed[0].get("role") == "assistant":
        trimmed = trimmed[1:]

    return trimmed


def build_messages(
    query: str,
    context: str,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Constrói lista de mensagens para o LLM com contexto RAG.

    Injeta o contexto meteorológico recuperado pelo RAG como
    uma mensagem de sistema embutida no conteúdo do usuário.

    Args:
        query: Pergunta do usuário.
        context: Contexto RAG recuperado.
        history: Histórico de mensagens (opcional).

    Returns:
        Lista de mensagens formatadas para a API.
    """
    messages: list[dict[str, str]] = []

    # Adiciona histórico trimado
    if history:
        messages.extend(trim_history(history))

    # Mensagem do usuário com contexto RAG embutido
    user_content = (
        f"[CONTEXTO METEOROLÓGICO RECUPERADO]\n{context}\n\n" f"[PERGUNTA DO USUÁRIO]\n{query}"
    )
    messages.append({"role": "user", "content": user_content})

    return messages


# ═══════════════════════════════════════════════════════════
# Funções de chamada ao LLM
# ═══════════════════════════════════════════════════════════


def ask(
    query: str,
    context: str,
    history: list[dict[str, str]] | None = None,
    settings: Settings | None = None,
    client: Anthropic | None = None,
) -> str:
    """Envia pergunta ao LLM e retorna resposta completa (non-streaming).

    Args:
        query: Pergunta do usuário.
        context: Contexto RAG recuperado.
        history: Histórico de chat.
        settings: Configurações (opcional).
        client: Cliente Anthropic pré-criado (opcional).

    Returns:
        Texto da resposta ou mensagem de fallback em caso de erro.
    """
    s = settings or Settings()
    llm = client or get_client(s)

    messages = build_messages(query, context, history)

    try:
        logger.info("LLM ask (non-streaming): model=%s, messages=%d", s.llm_model, len(messages))

        response = llm.messages.create(
            model=s.llm_model,
            max_tokens=s.llm_max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,  # type: ignore[arg-type]
        )

        text = response.content[0].text  # type: ignore[union-attr]
        logger.info("LLM response: %d chars", len(text))
        return str(text)

    except APITimeoutError:
        logger.error("LLM timeout após %ds", s.llm_timeout_seconds)
        return FALLBACK_MESSAGE
    except APIError as exc:
        logger.error("LLM API error: %s (status=%s)", exc.message, getattr(exc, "status_code", "?"))
        return FALLBACK_MESSAGE
    except Exception as exc:
        logger.error("LLM unexpected error: %s", exc)
        return FALLBACK_MESSAGE


def ask_stream(
    query: str,
    context: str,
    history: list[dict[str, str]] | None = None,
    settings: Settings | None = None,
    client: Anthropic | None = None,
) -> Generator[str, None, None]:
    """Envia pergunta ao LLM e retorna resposta via streaming (generator).

    Cada ``yield`` emite um trecho de texto conforme chega do LLM.
    Em caso de erro, emite a mensagem de fallback.

    Args:
        query: Pergunta do usuário.
        context: Contexto RAG recuperado.
        history: Histórico de chat.
        settings: Configurações (opcional).
        client: Cliente Anthropic pré-criado (opcional).

    Yields:
        Trechos de texto da resposta conforme chegam.
    """
    s = settings or Settings()
    llm = client or get_client(s)

    messages = build_messages(query, context, history)

    try:
        logger.info("LLM ask_stream: model=%s, messages=%d", s.llm_model, len(messages))

        with llm.messages.stream(
            model=s.llm_model,
            max_tokens=s.llm_max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,  # type: ignore[arg-type]
        ) as stream:
            full_text = ""
            for text in stream.text_stream:
                full_text += text
                yield text

            logger.info("LLM stream complete: %d chars", len(full_text))

    except APITimeoutError:
        logger.error("LLM stream timeout após %ds", s.llm_timeout_seconds)
        yield FALLBACK_MESSAGE
    except APIError as exc:
        logger.error("LLM stream API error: %s", exc.message)
        yield FALLBACK_MESSAGE
    except Exception as exc:
        logger.error("LLM stream unexpected error: %s", exc)
        yield FALLBACK_MESSAGE
