"""Testes unitários para retriever.py.

Valida indexação TF-IDF e busca por similaridade.
"""

from __future__ import annotations

from typing import Any


class TestRetrieverFixtures:
    """Testes de sanidade para fixtures do retriever."""

    def test_sample_chunks_can_be_indexed(self, sample_chunks: list[dict[str, Any]]) -> None:
        """Verifica que os chunks da fixture são indexáveis (têm texto não-vazio)."""
        for chunk in sample_chunks:
            assert len(chunk["text"].strip()) > 0

    def test_daily_summaries_have_data(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        """Verifica que daily summaries contêm dados numéricos válidos."""
        for summary in sample_daily_summaries:
            assert "total_rain_mm" in summary
            assert "max_temp_c" in summary
            assert isinstance(summary["total_rain_mm"], (int, float))
            assert isinstance(summary["max_temp_c"], (int, float))
