"""Tests for the INMET alerts client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.data.inmet import INMETClient, MG_STATE_CODE, SEVERITY_LABELS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alert(states: list[str], severity: str = "Amarelo", event: str = "Chuvas intensas") -> dict:
    return {
        "eventos": event,
        "evento": event,
        "severidade": severity,
        "inicio": "2026-01-01T06:00:00",
        "fim": "2026-01-01T18:00:00",
        "descricao": "Possibilidade de chuvas entre 30 e 60 mm/h.",
        "estados": states,
    }


def _make_municipio_alert(ufs: list[str]) -> dict:
    return {
        "evento": "Vendaval",
        "severidade": "Laranja",
        "municipios": [{"uf": uf} for uf in ufs],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestINMETClientGetActiveAlerts:
    def test_returns_list_when_api_returns_list(self):
        client = INMETClient()
        payload = [_make_alert(["MG", "SP"]), _make_alert(["RJ"])]
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.inmet.requests.get", return_value=mock_resp):
            result = client.get_active_alerts()

        assert result == payload

    def test_extracts_from_dict_with_avisos_key(self):
        client = INMETClient()
        alerts = [_make_alert(["MG"])]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"avisos": alerts}
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.inmet.requests.get", return_value=mock_resp):
            result = client.get_active_alerts()

        assert result == alerts

    def test_raises_on_http_error(self):
        import requests as req
        client = INMETClient()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("404")

        with patch("src.data.inmet.requests.get", return_value=mock_resp):
            with pytest.raises(req.HTTPError):
                client.get_active_alerts()

    def test_returns_empty_list_for_unexpected_response_format(self):
        client = INMETClient()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"unexpected_key": "value"}
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.inmet.requests.get", return_value=mock_resp):
            result = client.get_active_alerts()

        assert result == []


class TestINMETClientGetMgAlerts:
    def test_filters_mg_alerts(self):
        client = INMETClient()
        alerts = [
            _make_alert(["MG", "SP"]),
            _make_alert(["RJ", "ES"]),
            _make_alert(["MG"]),
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = alerts
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.inmet.requests.get", return_value=mock_resp):
            result = client.get_mg_alerts()

        assert len(result) == 2
        for a in result:
            assert "_summary" in a

    def test_mg_alerts_via_municipios(self):
        client = INMETClient()
        alert = _make_municipio_alert(["MG", "SP"])
        mock_resp = MagicMock()
        mock_resp.json.return_value = [alert]
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.inmet.requests.get", return_value=mock_resp):
            result = client.get_mg_alerts()

        assert len(result) == 1

    def test_no_mg_alerts_returns_empty(self):
        client = INMETClient()
        alerts = [_make_alert(["SP", "RJ"])]
        mock_resp = MagicMock()
        mock_resp.json.return_value = alerts
        mock_resp.raise_for_status.return_value = None

        with patch("src.data.inmet.requests.get", return_value=mock_resp):
            result = client.get_mg_alerts()

        assert result == []


class TestINMETBuildSummary:
    def test_summary_contains_event_name(self):
        alert = _make_alert(["MG"], event="Chuvas intensas")
        summary = INMETClient._build_summary(alert)
        assert "Chuvas intensas" in summary

    def test_summary_contains_severity_label(self):
        alert = _make_alert(["MG"], severity="Amarelo")
        summary = INMETClient._build_summary(alert)
        assert "Amarelo" in summary

    def test_summary_contains_estado_mg(self):
        alert = _make_alert(["MG"])
        summary = INMETClient._build_summary(alert)
        assert "Minas Gerais" in summary or "MG" in summary

    def test_html_stripped_from_description(self):
        alert = _make_alert(["MG"])
        alert["descricao"] = "<p>Chuvas <b>intensas</b> previstas.</p>"
        summary = INMETClient._build_summary(alert)
        assert "<p>" not in summary
        assert "<b>" not in summary
        assert "Chuvas" in summary


class TestSeverityLabels:
    def test_known_severities(self):
        assert "Vermelho" in SEVERITY_LABELS
        assert "Laranja" in SEVERITY_LABELS
        assert "Amarelo" in SEVERITY_LABELS

    def test_mg_state_code(self):
        assert MG_STATE_CODE == "MG"
