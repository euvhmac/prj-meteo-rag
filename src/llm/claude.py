"""Claude Haiku LLM client using the Anthropic API."""

from __future__ import annotations

import os
from typing import Any

import anthropic

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_MAX_TOKENS = 1024

SYSTEM_PROMPT = """Você é um agente meteorológico especializado em Minas Gerais, Brasil.
Sua função é responder perguntas sobre condições climáticas, chuvas, temperatura, umidade, \
ventos e alertas meteorológicos com base nas informações fornecidas.

Responda sempre em português do Brasil.
Seja claro, objetivo e preciso.
Quando não houver informação suficiente no contexto, informe ao usuário.
Use os dados fornecidos para embasar suas respostas.
"""


class ClaudeClient:
    """Wrapper around the Anthropic Claude API for meteorological Q&A.

    Args:
        api_key: Anthropic API key. Falls back to the ``ANTHROPIC_API_KEY``
            environment variable if not provided.
        model: Model identifier to use (default: claude-haiku-4-5).
        max_tokens: Maximum tokens in the LLM response.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY não encontrada. "
                "Defina a variável de ambiente ou passe api_key= ao construir ClaudeClient."
            )
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model
        self.max_tokens = max_tokens

    def answer(self, question: str, context: str = "") -> str:
        """Generate a natural language answer for a meteorological question.

        Args:
            question: User question in natural language.
            context: Retrieved RAG context to inject into the prompt.

        Returns:
            LLM-generated answer as a plain string.

        Raises:
            anthropic.APIError: On API failures.
        """
        user_content = self._build_user_prompt(question, context)
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return self._extract_text(message)

    @staticmethod
    def _build_user_prompt(question: str, context: str) -> str:
        if context.strip():
            return (
                "Com base nas seguintes informações meteorológicas:\n\n"
                f"{context}\n\n"
                f"Pergunta: {question}"
            )
        return f"Pergunta: {question}"

    @staticmethod
    def _extract_text(message: Any) -> str:
        for block in message.content:
            if hasattr(block, "text"):
                return block.text
        return ""
