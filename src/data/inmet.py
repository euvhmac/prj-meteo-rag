"""INMET (Instituto Nacional de Meteorologia) alerts client."""

from __future__ import annotations

import os
from typing import Any

import requests

INMET_BASE_URL = os.getenv(
    "INMET_BASE_URL", "https://apiprevmet3.inmet.gov.br"
)

# IBGE state code for Minas Gerais
MG_STATE_CODE = "MG"

SEVERITY_LABELS: dict[str, str] = {
    "Vermelho": "Vermelho (Grande Perigo)",
    "Laranja": "Laranja (Perigo)",
    "Amarelo": "Amarelo (Atenção)",
    "Cinza": "Cinza (Sem Risco)",
}


class INMETClient:
    """Client for the INMET public alerts API."""

    def __init__(self, base_url: str = INMET_BASE_URL, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Fetch all currently active weather alerts from INMET.

        Returns:
            List of alert dictionaries from the INMET API.

        Raises:
            requests.HTTPError: If the API returns a non-2xx status.
        """
        response = requests.get(
            f"{self.base_url}/avisos/ativos", timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        # The API may return a list or a dict with a list
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("avisos", "data", "results"):
                if isinstance(data.get(key), list):
                    return data[key]
        return []

    def get_mg_alerts(self) -> list[dict[str, Any]]:
        """Filter active alerts to those affecting Minas Gerais.

        Returns:
            List of alerts for MG, each with a human-readable summary.
        """
        alerts = self.get_active_alerts()
        mg_alerts: list[dict[str, Any]] = []
        for alert in alerts:
            states = self._extract_states(alert)
            if MG_STATE_CODE in states:
                alert["_summary"] = self._build_summary(alert)
                mg_alerts.append(alert)
        return mg_alerts

    @staticmethod
    def _extract_states(alert: dict[str, Any]) -> list[str]:
        """Extract list of affected state codes from an alert record."""
        # INMET API may use different field names depending on version
        for field in ("estados", "uf", "state", "states"):
            value = alert.get(field)
            if isinstance(value, list):
                return [str(s).upper() for s in value]
            if isinstance(value, str):
                return [s.strip().upper() for s in value.split(",")]
        # Try nested municipios/states structure
        municipios = alert.get("municipios", [])
        if isinstance(municipios, list):
            states: list[str] = []
            for m in municipios:
                if isinstance(m, dict):
                    uf = m.get("uf") or m.get("estado") or m.get("state", "")
                    if uf:
                        states.append(str(uf).upper())
            return list(set(states))
        return []

    @staticmethod
    def _build_summary(alert: dict[str, Any]) -> str:
        """Build a human-readable Portuguese summary for a given alert."""
        severity = alert.get("severidade") or alert.get("severity") or alert.get("nivel", "")
        label = SEVERITY_LABELS.get(str(severity), str(severity))

        event = (
            alert.get("evento")
            or alert.get("event")
            or alert.get("tipo")
            or alert.get("descricao", "Evento meteorológico")
        )
        start = alert.get("inicio") or alert.get("dtInicio") or alert.get("start", "")
        end = alert.get("fim") or alert.get("dtFim") or alert.get("end", "")
        description = (
            alert.get("descricao")
            or alert.get("descricaoHTML")
            or alert.get("description", "")
        )
        # Strip HTML tags if present
        if "<" in str(description):
            import re
            description = re.sub(r"<[^>]+>", " ", str(description)).strip()

        parts = [f"Alerta INMET: {event}"]
        if label:
            parts.append(f"Nível: {label}")
        if start:
            parts.append(f"Início: {start}")
        if end:
            parts.append(f"Fim: {end}")
        if description:
            parts.append(f"Descrição: {description}")
        parts.append("Estado: Minas Gerais (MG)")
        return ". ".join(parts) + "."
