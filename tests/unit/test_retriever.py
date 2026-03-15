"""Testes unitários para retriever.py.

Valida indexação TF-IDF e busca por similaridade.
"""

from __future__ import annotations

from typing import Any

from meteorag.rag.retriever import TFIDFRetriever

# ══════════════════════════════════════════════════════════
# TFIDFRetriever
# ══════════════════════════════════════════════════════════


class TestTFIDFRetriever:
    """Testes para o retriever TF-IDF."""

    def test_index_returns_count(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        count = retriever.index(sample_chunks)
        assert count == len(sample_chunks)

    def test_is_indexed_after_index(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        assert retriever.is_indexed is False
        retriever.index(sample_chunks)
        assert retriever.is_indexed is True

    def test_chunk_count(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        assert retriever.chunk_count == len(sample_chunks)

    def test_search_returns_results(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("chuva Juiz de Fora")
        assert len(results) > 0

    def test_search_results_have_score(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("chuva")
        for r in results:
            assert "score" in r
            assert r["score"] > 0

    def test_search_results_sorted_by_score(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("chuva forte")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_respects_top_k(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("chuva", top_k=2)
        assert len(results) <= 2

    def test_search_empty_query_returns_empty(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("")
        assert results == []

    def test_search_without_index_returns_empty(self) -> None:
        retriever = TFIDFRetriever()
        results = retriever.search("chuva")
        assert results == []

    def test_filter_by_type(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("chuva", filter_type="alert")
        for r in results:
            assert r["metadata"]["type"] == "alert"

    def test_filter_by_city(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("chuva", filter_city="Juiz de Fora")
        for r in results:
            assert r["metadata"]["city"] == "Juiz de Fora"

    def test_index_empty_chunks(self) -> None:
        retriever = TFIDFRetriever()
        count = retriever.index([])
        assert count == 0
        assert retriever.is_indexed is False

    def test_index_chunks_with_empty_text(self) -> None:
        retriever = TFIDFRetriever()
        bad_chunks = [
            {"text": "", "metadata": {"city": "Test", "date": "2024-01-01", "type": "daily"}},
            {"text": "   ", "metadata": {"city": "Test", "date": "2024-01-01", "type": "daily"}},
        ]
        count = retriever.index(bad_chunks)
        assert count == 0

    def test_reindex_replaces_data(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        assert retriever.chunk_count == len(sample_chunks)

        # Re-indexa com menos dados
        retriever.index(sample_chunks[:2])
        assert retriever.chunk_count == 2

    def test_clear_resets(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        retriever.clear()
        assert retriever.is_indexed is False
        assert retriever.chunk_count == 0

    def test_get_all_chunks(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        all_chunks = retriever.get_all_chunks()
        assert len(all_chunks) == len(sample_chunks)

    def test_rain_query_finds_rain_chunks(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("chuva forte precipitação")
        # Pelo menos o chunk de alerta ou diário com chuva deve aparecer
        assert len(results) > 0
        texts = " ".join(r["text"] for r in results)
        assert "chuva" in texts.lower() or "Chuva" in texts

    def test_alert_query_finds_alert(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("alerta meteorológico perigo")
        assert any(r["metadata"]["type"] == "alert" for r in results)

    def test_temperature_query(self, sample_chunks: list[dict[str, Any]]) -> None:
        retriever = TFIDFRetriever()
        retriever.index(sample_chunks)
        results = retriever.search("temperatura máxima")
        assert len(results) > 0


# ══════════════════════════════════════════════════════════
# Fixture sanity checks (preservados)
# ══════════════════════════════════════════════════════════


class TestRetrieverFixtures:
    """Testes de sanidade para fixtures do retriever."""

    def test_sample_chunks_can_be_indexed(self, sample_chunks: list[dict[str, Any]]) -> None:
        for chunk in sample_chunks:
            assert len(chunk["text"].strip()) > 0

    def test_daily_summaries_have_data(self, sample_daily_summaries: list[dict[str, Any]]) -> None:
        for summary in sample_daily_summaries:
            assert "total_rain_mm" in summary
            assert "max_temp_c" in summary
            assert isinstance(summary["total_rain_mm"], (int, float))
            assert isinstance(summary["max_temp_c"], (int, float))
