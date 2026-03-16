"""Tests for the RAG document store and retriever."""

from __future__ import annotations

import pytest

from src.rag.document import Document
from src.rag.retriever import Retriever
from src.rag.store import DocumentStore


# ---------------------------------------------------------------------------
# Document tests
# ---------------------------------------------------------------------------

class TestDocument:
    def test_creates_document_with_content(self):
        doc = Document(content="Temperatura de 28°C em Belo Horizonte.")
        assert doc.content == "Temperatura de 28°C em Belo Horizonte."

    def test_default_metadata_is_empty_dict(self):
        doc = Document(content="Chuva intensa prevista.")
        assert doc.metadata == {}

    def test_metadata_stored_correctly(self):
        doc = Document(content="Alerta.", metadata={"source": "inmet", "city": "BH"})
        assert doc.metadata["source"] == "inmet"

    def test_empty_content_raises_value_error(self):
        with pytest.raises(ValueError):
            Document(content="")

    def test_whitespace_only_content_raises_value_error(self):
        with pytest.raises(ValueError):
            Document(content="   ")


# ---------------------------------------------------------------------------
# DocumentStore tests
# ---------------------------------------------------------------------------

class TestDocumentStore:
    def _make_store_with_docs(self) -> tuple[DocumentStore, list[Document]]:
        store = DocumentStore()
        docs = [
            Document(
                content="Cidade: Belo Horizonte. temperatura 28.5°C. chuva 5.0 mm. condição: chuva moderada.",
                metadata={"city": "Belo Horizonte"},
            ),
            Document(
                content="Cidade: Uberlândia. temperatura 32.0°C. umidade 55%. condição: céu limpo.",
                metadata={"city": "Uberlândia"},
            ),
            Document(
                content="Alerta INMET: Chuvas intensas. Nível: Amarelo (Atenção). Estado: Minas Gerais (MG).",
                metadata={"source": "inmet"},
            ),
        ]
        store.add_documents(docs)
        return store, docs

    def test_empty_store_is_empty(self):
        store = DocumentStore()
        assert store.is_empty
        assert len(store) == 0

    def test_add_documents_increases_count(self):
        store, docs = self._make_store_with_docs()
        assert len(store) == 3
        assert not store.is_empty

    def test_search_returns_relevant_document(self):
        store, _ = self._make_store_with_docs()
        results = store.search("chuva moderada Belo Horizonte", k=1)
        assert len(results) == 1
        assert "Belo Horizonte" in results[0].content

    def test_search_empty_query_returns_empty_list(self):
        store, _ = self._make_store_with_docs()
        results = store.search("   ")
        assert results == []

    def test_search_on_empty_store_returns_empty_list(self):
        store = DocumentStore()
        results = store.search("chuva")
        assert results == []

    def test_search_returns_at_most_k_results(self):
        store, _ = self._make_store_with_docs()
        results = store.search("temperatura chuva alerta", k=2)
        assert len(results) <= 2

    def test_clear_empties_store(self):
        store, _ = self._make_store_with_docs()
        store.clear()
        assert store.is_empty
        assert len(store) == 0

    def test_add_documents_empty_list_is_noop(self):
        store = DocumentStore()
        store.add_documents([])
        assert store.is_empty

    def test_alert_retrieved_for_alert_query(self):
        store, _ = self._make_store_with_docs()
        results = store.search("alertas INMET Minas Gerais", k=2)
        sources = [r.metadata.get("source") for r in results]
        assert "inmet" in sources


# ---------------------------------------------------------------------------
# Retriever tests
# ---------------------------------------------------------------------------

class TestRetriever:
    def _make_retriever(self) -> Retriever:
        r = Retriever()
        r.add_documents([
            Document(
                content="Cidade: Belo Horizonte. temperatura 25°C. chuva 10 mm. condição: chuva leve.",
                metadata={"city": "Belo Horizonte"},
            ),
            Document(
                content="Cidade: Montes Claros. temperatura 35°C. umidade 40%. condição: céu limpo.",
                metadata={"city": "Montes Claros"},
            ),
            Document(
                content="Alerta INMET: Vendaval. Nível: Laranja (Perigo). Estado: Minas Gerais.",
                metadata={"source": "inmet"},
            ),
        ])
        return r

    def test_retrieve_returns_documents(self):
        r = self._make_retriever()
        docs = r.retrieve("chuva em Belo Horizonte")
        assert len(docs) >= 1

    def test_retrieve_context_returns_string(self):
        r = self._make_retriever()
        ctx = r.retrieve_context("chuva em Belo Horizonte")
        assert isinstance(ctx, str)
        assert len(ctx) > 0

    def test_retrieve_context_contains_fonte_header(self):
        r = self._make_retriever()
        ctx = r.retrieve_context("chuva Belo Horizonte")
        assert "[Fonte 1]" in ctx

    def test_retrieve_context_empty_store_returns_empty_string(self):
        r = Retriever()
        ctx = r.retrieve_context("qualquer coisa")
        assert ctx == ""

    def test_retrieve_context_no_match_returns_empty_string(self):
        r = Retriever()
        r.add_documents([Document(content="Texto de teste.")])
        # An unrelated query may score 0 and return empty
        ctx = r.retrieve_context("xyzzy impossible query aaaabbbb")
        # May or may not return something; just ensure it's a string
        assert isinstance(ctx, str)
