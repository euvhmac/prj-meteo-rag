"""Testes de integração para pipeline.py.

Marcados com @pytest.mark.integration — requerem .env configurado.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
class TestRAGPipelineIntegration:
    """Testes de integração do pipeline completo (pulados no CI padrão)."""

    def test_placeholder(self) -> None:
        """Placeholder — será implementado na Sprint 1."""
        pytest.skip("Implementação na Sprint 1")
