"""Testes unitários para chunker.py.

Valida a conversão de dados meteorológicos em chunks de texto.
"""

from __future__ import annotations

from typing import Any


class TestChunkFixtures:
    """Testes de sanidade para as fixtures de chunks."""

    def test_chunks_fixture_has_data(self, sample_chunks: list[dict[str, Any]]) -> None:
        """Verifica que a fixture de chunks contém dados."""
        assert len(sample_chunks) > 0

    def test_chunks_have_text_and_metadata(self, sample_chunks: list[dict[str, Any]]) -> None:
        """Verifica que cada chunk tem text e metadata."""
        for chunk in sample_chunks:
            assert "text" in chunk
            assert "metadata" in chunk
            assert isinstance(chunk["text"], str)
            assert len(chunk["text"]) > 0

    def test_chunks_metadata_has_required_fields(self, sample_chunks: list[dict[str, Any]]) -> None:
        """Verifica que metadata contém city, date e type."""
        for chunk in sample_chunks:
            meta = chunk["metadata"]
            assert "city" in meta
            assert "date" in meta
            assert "type" in meta

    def test_chunk_types_are_valid(self, sample_chunks: list[dict[str, Any]]) -> None:
        """Verifica que os tipos de chunk são válidos."""
        valid_types = {"hourly", "daily", "alert", "context"}
        for chunk in sample_chunks:
            assert chunk["metadata"]["type"] in valid_types

    def test_chunks_under_max_size(self, sample_chunks: list[dict[str, Any]]) -> None:
        """Verifica que todos os chunks respeitam o tamanho máximo de 512 chars."""
        max_size = 512
        for chunk in sample_chunks:
            assert (
                len(chunk["text"]) <= max_size
            ), f"Chunk excede {max_size} chars: {len(chunk['text'])} chars"
