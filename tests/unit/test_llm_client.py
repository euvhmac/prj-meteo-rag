"""Testes unitários para meteorag.llm.client.

Utiliza mocks do Anthropic SDK para validar:
- Criação do cliente (get_client)
- Trim de histórico (trim_history)
- Construção de mensagens (build_messages)
- ask() non-streaming com sucesso e fallback
- ask_stream() streaming com sucesso e fallback
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from meteorag.config import Settings
from meteorag.llm.client import (
    FALLBACK_MESSAGE,
    MAX_HISTORY_MESSAGES,
    SYSTEM_PROMPT,
    ask,
    ask_stream,
    build_messages,
    get_client,
    trim_history,
)

# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════


@pytest.fixture()
def test_settings() -> Settings:
    """Settings de teste com valores controlados."""
    return Settings(
        anthropic_api_key="test-key-123",
        anthropic_base_url="https://test.example.com/endpoint",
        llm_model="test-model",
        llm_max_tokens=1024,
        llm_timeout_seconds=30,
    )


@pytest.fixture()
def mock_anthropic_client() -> MagicMock:
    """Mock do Anthropic client."""
    client = MagicMock()

    # Mock para ask() — non-streaming
    mock_response = MagicMock()
    mock_content_block = MagicMock()
    mock_content_block.text = "Resposta do LLM de teste."
    mock_response.content = [mock_content_block]
    client.messages.create.return_value = mock_response

    return client


@pytest.fixture()
def sample_history() -> list[dict[str, str]]:
    """Histórico de chat de exemplo."""
    return [
        {"role": "user", "content": "Olá!"},
        {"role": "assistant", "content": "Olá! Como posso ajudar?"},
        {"role": "user", "content": "Choveu hoje?"},
        {"role": "assistant", "content": "Deixe-me verificar os dados..."},
    ]


# ═══════════════════════════════════════════════════════════
# Tests: get_client
# ═══════════════════════════════════════════════════════════


class TestGetClient:
    """Testes para a factory get_client."""

    @patch("meteorag.llm.client.Anthropic")
    def test_creates_client_with_base_url(
        self, mock_cls: MagicMock, test_settings: Settings
    ) -> None:
        """Deve criar cliente com base_url quando configurada."""
        get_client(test_settings)

        mock_cls.assert_called_once_with(
            api_key="test-key-123",
            timeout=30.0,
            base_url="https://test.example.com/endpoint",
        )

    @patch("meteorag.llm.client.Anthropic")
    def test_creates_client_without_base_url(self, mock_cls: MagicMock) -> None:
        """Deve criar cliente sem base_url quando não configurada."""
        settings = Settings(
            anthropic_api_key="key-abc",
            anthropic_base_url="",
            llm_timeout_seconds=60,
        )
        get_client(settings)

        mock_cls.assert_called_once_with(
            api_key="key-abc",
            timeout=60.0,
        )

    @patch("meteorag.llm.client.Anthropic")
    def test_returns_anthropic_instance(self, mock_cls: MagicMock, test_settings: Settings) -> None:
        """Deve retornar a instância criada."""
        expected = MagicMock()
        mock_cls.return_value = expected

        result = get_client(test_settings)
        assert result is expected


# ═══════════════════════════════════════════════════════════
# Tests: trim_history
# ═══════════════════════════════════════════════════════════


class TestTrimHistory:
    """Testes para trim_history."""

    def test_short_history_unchanged(self, sample_history: list[dict[str, str]]) -> None:
        """Histórico dentro do limite não deve ser alterado."""
        result = trim_history(sample_history)
        assert result == sample_history

    def test_empty_history(self) -> None:
        """Histórico vazio retorna lista vazia."""
        assert trim_history([]) == []

    def test_trims_to_max_messages(self) -> None:
        """Deve manter apenas as últimas N mensagens."""
        messages = []
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": f"msg {i}"})

        result = trim_history(messages, max_messages=10)
        assert len(result) == 10
        assert result[0]["content"] == "msg 10"

    def test_ensures_starts_with_user(self) -> None:
        """Se o trim resulta em assistente primeiro, remove uma mensagem."""
        messages = [
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a3"},
        ]
        result = trim_history(messages, max_messages=4)
        # Últimas 4: u1, a2, u2, a3 — começa com user, OK
        assert result[0]["role"] == "user"

    def test_returns_new_list(self, sample_history: list[dict[str, str]]) -> None:
        """Deve retornar uma nova lista, não a original."""
        result = trim_history(sample_history)
        assert result is not sample_history

    def test_default_max_is_ten(self) -> None:
        """O default de max_messages deve ser MAX_HISTORY_MESSAGES (10)."""
        messages = [{"role": "user", "content": f"m{i}"} for i in range(15)]
        result = trim_history(messages)
        assert len(result) == MAX_HISTORY_MESSAGES


# ═══════════════════════════════════════════════════════════
# Tests: build_messages
# ═══════════════════════════════════════════════════════════


class TestBuildMessages:
    """Testes para build_messages."""

    def test_basic_message(self) -> None:
        """Deve construir mensagem com query e contexto."""
        result = build_messages("Vai chover?", "Contexto: chuva 10mm")

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "[CONTEXTO METEOROLÓGICO RECUPERADO]" in result[0]["content"]
        assert "Contexto: chuva 10mm" in result[0]["content"]
        assert "[PERGUNTA DO USUÁRIO]" in result[0]["content"]
        assert "Vai chover?" in result[0]["content"]

    def test_with_history(self, sample_history: list[dict[str, str]]) -> None:
        """Deve incluir histórico antes da mensagem atual."""
        result = build_messages("Nova pergunta", "contexto", history=sample_history)

        # 4 histórico + 1 nova = 5
        assert len(result) == 5
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Olá!"
        assert result[-1]["role"] == "user"
        assert "Nova pergunta" in result[-1]["content"]

    def test_without_history(self) -> None:
        """Sem histórico deve ter apenas a mensagem atual."""
        result = build_messages("pergunta", "contexto", history=None)
        assert len(result) == 1

    def test_history_is_trimmed(self) -> None:
        """Histórico grande deve ser trimado."""
        big_history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"h{i}"} for i in range(20)
        ]
        result = build_messages("q", "c", history=big_history)
        # max 10 do histórico + 1 nova
        assert len(result) <= MAX_HISTORY_MESSAGES + 1


# ═══════════════════════════════════════════════════════════
# Tests: ask (non-streaming)
# ═══════════════════════════════════════════════════════════


class TestAsk:
    """Testes para ask() non-streaming."""

    def test_successful_response(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve retornar texto da resposta do LLM."""
        result = ask(
            query="Choveu hoje?",
            context="Dados: chuva 10mm em JF",
            settings=test_settings,
            client=mock_anthropic_client,
        )

        assert result == "Resposta do LLM de teste."
        mock_anthropic_client.messages.create.assert_called_once()

    def test_passes_correct_params(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve passar model, max_tokens, system e messages corretos."""
        ask(
            query="pergunta",
            context="contexto",
            settings=test_settings,
            client=mock_anthropic_client,
        )

        call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["system"] == SYSTEM_PROMPT
        assert len(call_kwargs["messages"]) == 1
        assert call_kwargs["messages"][0]["role"] == "user"

    def test_includes_history(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
        sample_history: list[dict[str, str]],
    ) -> None:
        """Deve incluir histórico nas mensagens."""
        ask(
            query="outra pergunta",
            context="dados",
            history=sample_history,
            settings=test_settings,
            client=mock_anthropic_client,
        )

        call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
        assert len(call_kwargs["messages"]) == 5  # 4 histórico + 1 nova

    def test_fallback_on_timeout(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve retornar fallback em caso de timeout."""
        from anthropic import APITimeoutError

        mock_anthropic_client.messages.create.side_effect = APITimeoutError(request=MagicMock())

        result = ask("q", "c", settings=test_settings, client=mock_anthropic_client)
        assert result == FALLBACK_MESSAGE

    def test_fallback_on_api_error(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve retornar fallback em caso de APIError."""
        from anthropic import APIError

        mock_request = MagicMock()
        mock_anthropic_client.messages.create.side_effect = APIError(
            message="Server error",
            request=mock_request,
            body=None,
        )

        result = ask("q", "c", settings=test_settings, client=mock_anthropic_client)
        assert result == FALLBACK_MESSAGE

    def test_fallback_on_unexpected_error(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve retornar fallback em caso de erro inesperado."""
        mock_anthropic_client.messages.create.side_effect = RuntimeError("boom")

        result = ask("q", "c", settings=test_settings, client=mock_anthropic_client)
        assert result == FALLBACK_MESSAGE


# ═══════════════════════════════════════════════════════════
# Tests: ask_stream
# ═══════════════════════════════════════════════════════════


class TestAskStream:
    """Testes para ask_stream() streaming."""

    def test_yields_text_chunks(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve fazer yield de chunks de texto."""
        # Mock do stream context manager
        mock_stream = MagicMock()
        mock_stream.text_stream = iter(["Olá", ", ", "mundo", "!"])
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_anthropic_client.messages.stream.return_value = mock_stream

        chunks = list(ask_stream("q", "c", settings=test_settings, client=mock_anthropic_client))

        assert chunks == ["Olá", ", ", "mundo", "!"]

    def test_passes_correct_params(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve passar parâmetros corretos para stream."""
        mock_stream = MagicMock()
        mock_stream.text_stream = iter(["ok"])
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_anthropic_client.messages.stream.return_value = mock_stream

        list(ask_stream("q", "c", settings=test_settings, client=mock_anthropic_client))

        call_kwargs = mock_anthropic_client.messages.stream.call_args.kwargs
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["system"] == SYSTEM_PROMPT

    def test_fallback_on_timeout(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve yield fallback em caso de timeout."""
        from anthropic import APITimeoutError

        mock_anthropic_client.messages.stream.side_effect = APITimeoutError(request=MagicMock())

        chunks = list(ask_stream("q", "c", settings=test_settings, client=mock_anthropic_client))
        assert chunks == [FALLBACK_MESSAGE]

    def test_fallback_on_api_error(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve yield fallback em caso de APIError."""
        from anthropic import APIError

        mock_anthropic_client.messages.stream.side_effect = APIError(
            message="err", request=MagicMock(), body=None
        )

        chunks = list(ask_stream("q", "c", settings=test_settings, client=mock_anthropic_client))
        assert chunks == [FALLBACK_MESSAGE]

    def test_fallback_on_unexpected_error(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
    ) -> None:
        """Deve yield fallback em caso de erro inesperado."""
        mock_anthropic_client.messages.stream.side_effect = ValueError("oops")

        chunks = list(ask_stream("q", "c", settings=test_settings, client=mock_anthropic_client))
        assert chunks == [FALLBACK_MESSAGE]

    def test_with_history(
        self,
        test_settings: Settings,
        mock_anthropic_client: MagicMock,
        sample_history: list[dict[str, str]],
    ) -> None:
        """Deve incluir histórico nas mensagens do stream."""
        mock_stream = MagicMock()
        mock_stream.text_stream = iter(["resp"])
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_anthropic_client.messages.stream.return_value = mock_stream

        list(
            ask_stream(
                "q",
                "c",
                history=sample_history,
                settings=test_settings,
                client=mock_anthropic_client,
            )
        )

        call_kwargs = mock_anthropic_client.messages.stream.call_args.kwargs
        assert len(call_kwargs["messages"]) == 5


# ═══════════════════════════════════════════════════════════
# Tests: SYSTEM_PROMPT
# ═══════════════════════════════════════════════════════════


class TestSystemPrompt:
    """Testes para o system prompt."""

    def test_prompt_mentions_meteorag(self) -> None:
        """O prompt deve mencionar MeteoRAG."""
        assert "MeteoRAG" in SYSTEM_PROMPT

    def test_prompt_mentions_inmet(self) -> None:
        """O prompt deve mencionar INMET."""
        assert "INMET" in SYSTEM_PROMPT

    def test_prompt_mentions_minas_gerais(self) -> None:
        """O prompt deve mencionar Minas Gerais."""
        assert "Minas Gerais" in SYSTEM_PROMPT

    def test_prompt_has_rain_interpretation(self) -> None:
        """O prompt deve ter regras de interpretação de chuva."""
        assert "mm" in SYSTEM_PROMPT
        assert "fraca" in SYSTEM_PROMPT or "forte" in SYSTEM_PROMPT

    def test_prompt_has_temperature_interpretation(self) -> None:
        """O prompt deve ter regras de interpretação de temperatura."""
        assert "°C" in SYSTEM_PROMPT

    def test_prompt_is_portuguese(self) -> None:
        """O prompt deve estar em português."""
        assert "Você é" in SYSTEM_PROMPT


# ═══════════════════════════════════════════════════════════
# Tests: Constants
# ═══════════════════════════════════════════════════════════


class TestConstants:
    """Testes para constantes do módulo."""

    def test_max_history_is_ten(self) -> None:
        """MAX_HISTORY_MESSAGES deve ser 10."""
        assert MAX_HISTORY_MESSAGES == 10

    def test_fallback_message_is_friendly(self) -> None:
        """Mensagem de fallback deve ser amigável e informativa."""
        assert "Desculpe" in FALLBACK_MESSAGE or "desculpe" in FALLBACK_MESSAGE
        assert len(FALLBACK_MESSAGE) > 20
