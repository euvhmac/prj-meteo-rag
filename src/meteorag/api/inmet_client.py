"""Cliente HTTP para a API pública do INMET.

Responsável por toda comunicação com https://apitempo.inmet.gov.br.
Implementa retry com backoff exponencial, cache em memória com TTL
e normalização de valores inválidos (-9999, 9999, null, "").
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, timedelta
from typing import Any

import requests

from meteorag.config import Settings
from meteorag.metrics import INMET_LATENCY_SECONDS, INMET_REQUESTS_TOTAL

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Circuit Breaker
# ═══════════════════════════════════════════════════════════

_CB_FAILURE_THRESHOLD: int = 5
"""Número de falhas consecutivas para abrir o circuit breaker."""

_CB_COOLDOWN_SECONDS: int = 300  # 5 minutos
"""Tempo de cooldown antes de tentar reconectar."""


class _CircuitBreaker:
    """Circuit breaker simples para a API INMET.

    Após ``_CB_FAILURE_THRESHOLD`` falhas consecutivas, entra em estado
    *open* por ``_CB_COOLDOWN_SECONDS``. Após o cooldown, permite uma
    tentativa (*half-open*). Se sucesso, volta a *closed*.

    Thread-safe via lock.
    """

    __slots__ = ("_consecutive_failures", "_last_failure_time", "_lock", "_state")

    def __init__(self) -> None:
        self._consecutive_failures: int = 0
        self._last_failure_time: float = 0.0
        self._state: str = "closed"  # closed | open | half-open
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        """Estado atual do circuit breaker."""
        with self._lock:
            if self._state == "open":
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= _CB_COOLDOWN_SECONDS:
                    self._state = "half-open"
            return self._state

    @property
    def is_open(self) -> bool:
        """True se o circuito está aberto (API indisponível)."""
        return self.state == "open"

    def record_success(self) -> None:
        """Registra sucesso — reseta contador e fecha o circuito."""
        with self._lock:
            self._consecutive_failures = 0
            self._state = "closed"

    def record_failure(self) -> None:
        """Registra falha — incrementa contador e possivelmente abre o circuito."""
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.monotonic()
            if self._consecutive_failures >= _CB_FAILURE_THRESHOLD:
                self._state = "open"
                logger.warning(
                    "Circuit breaker OPEN: %d falhas consecutivas. " "Cooldown de %ds.",
                    self._consecutive_failures,
                    _CB_COOLDOWN_SECONDS,
                )

    def reset(self) -> None:
        """Reseta o circuit breaker para o estado inicial."""
        with self._lock:
            self._consecutive_failures = 0
            self._last_failure_time = 0.0
            self._state = "closed"


# ═══════════════════════════════════════════════════════════
# Estações prioritárias da Zona da Mata e região
# ═══════════════════════════════════════════════════════════
MG_PRIORITY_STATIONS: dict[str, str] = {
    "A518": "Juiz de Fora",
    "A519": "Barbacena",
    "A520": "Viçosa",
    "A521": "Belo Horizonte",
    "A527": "Caratinga",
    "A555": "Muriaé",
}
"""Mapeamento código → nome das estações prioritárias de MG."""

# Valores sentinela que a API INMET usa para dados inválidos
_INVALID_SENTINELS: frozenset[str] = frozenset({"-9999", "9999", "-9999.0", "9999.0"})


# ═══════════════════════════════════════════════════════════
# Funções de normalização
# ═══════════════════════════════════════════════════════════


def parse_value(raw: Any) -> float | None:
    """Converte um valor bruto da API INMET para ``float`` ou ``None``.

    Regras:
        - ``None``, ``""`` e strings sentinela (``-9999``, ``9999``) → ``None``
        - Valores numéricos válidos → ``float``

    Args:
        raw: Valor retornado pela API (str, int, float ou None).

    Returns:
        Valor numérico normalizado ou ``None`` se inválido.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s in _INVALID_SENTINELS:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_observation(raw_obs: dict[str, Any]) -> dict[str, Any]:
    """Normaliza uma observação horária bruta da API INMET.

    Converte todos os campos numéricos via ``parse_value`` e preserva
    os campos de identificação como strings.

    Args:
        raw_obs: Dicionário de uma observação conforme retornado pela API.

    Returns:
        Dicionário normalizado com campos numéricos como ``float | None``.
    """
    return {
        "station_code": raw_obs.get("CD_ESTACAO", ""),
        "date": raw_obs.get("DT_MEDICAO", ""),
        "time": raw_obs.get("HR_MEDICAO", ""),
        "rain_mm": parse_value(raw_obs.get("CHUVA")),
        "temp_c": parse_value(raw_obs.get("TEM_INS")),
        "temp_max_c": parse_value(raw_obs.get("TEM_MAX")),
        "temp_min_c": parse_value(raw_obs.get("TEM_MIN")),
        "humidity_pct": parse_value(raw_obs.get("UMD_INS")),
        "wind_speed_ms": parse_value(raw_obs.get("VEN_VEL")),
        "wind_dir_deg": parse_value(raw_obs.get("VEN_DIR")),
        "pressure_hpa": parse_value(raw_obs.get("PRE_INS")),
        "radiation_kjm2": parse_value(raw_obs.get("RAD_GLO")),
    }


def get_daily_summary(
    observations: list[dict[str, Any]],
    city: str,
    station_code: str,
    target_date: str,
) -> dict[str, Any]:
    """Agrega observações horárias normalizadas em um sumário diário.

    Args:
        observations: Lista de observações já normalizadas (output de ``parse_observation``).
        city: Nome da cidade.
        station_code: Código da estação INMET.
        target_date: Data no formato ``YYYY-MM-DD``.

    Returns:
        Dicionário com estatísticas do dia (chuva total, temp máx/mín,
        umidade média, contagem de observações).
    """
    day_obs = [o for o in observations if o["date"] == target_date]

    rain_values = [o["rain_mm"] for o in day_obs if o["rain_mm"] is not None]
    temp_max_values = [o["temp_max_c"] for o in day_obs if o["temp_max_c"] is not None]
    temp_min_values = [o["temp_min_c"] for o in day_obs if o["temp_min_c"] is not None]
    humidity_values = [o["humidity_pct"] for o in day_obs if o["humidity_pct"] is not None]

    total_rain = round(sum(rain_values), 1) if rain_values else None
    max_temp = max(temp_max_values) if temp_max_values else None
    min_temp = min(temp_min_values) if temp_min_values else None
    avg_humidity = (
        round(sum(humidity_values) / len(humidity_values), 2) if humidity_values else None
    )

    return {
        "city": city,
        "station_code": station_code,
        "date": target_date,
        "total_rain_mm": total_rain,
        "max_temp_c": max_temp,
        "min_temp_c": min_temp,
        "avg_humidity_pct": avg_humidity,
        "observation_count": len(day_obs),
    }


# ═══════════════════════════════════════════════════════════
# Cache entry helper
# ═══════════════════════════════════════════════════════════


class _CacheEntry:
    """Entrada no cache em memória com TTL."""

    __slots__ = ("data", "expires_at")

    def __init__(self, data: Any, ttl_seconds: int) -> None:
        self.data = data
        self.expires_at = time.monotonic() + ttl_seconds

    @property
    def is_valid(self) -> bool:
        """Verifica se a entrada ainda está dentro do TTL."""
        return time.monotonic() < self.expires_at


# ═══════════════════════════════════════════════════════════
# Cliente principal
# ═══════════════════════════════════════════════════════════


class INMETClient:
    """Cliente HTTP para a API pública do INMET com retry e cache.

    Attributes:
        base_url: URL base da API INMET.
        timeout: Timeout em segundos para cada requisição.
        max_retries: Número máximo de tentativas com backoff exponencial.
        cache_ttl: TTL do cache em memória em segundos.

    Example:
        >>> client = INMETClient()
        >>> stations = client.get_stations()
        >>> mg = client.get_mg_stations()
    """

    # Circuit breaker compartilhado entre instâncias
    _circuit_breaker: _CircuitBreaker = _CircuitBreaker()

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self.base_url = self._settings.inmet_base_url.rstrip("/")
        self.timeout = self._settings.inmet_timeout_seconds
        self.max_retries = self._settings.inmet_retry_max
        self.cache_ttl = self._settings.inmet_cache_ttl_seconds
        self._cache: dict[str, _CacheEntry] = {}
        self._session = requests.Session()

    @property
    def circuit_breaker_state(self) -> str:
        """Estado atual do circuit breaker (closed, open, half-open)."""
        return self._circuit_breaker.state

    # ── HTTP com retry ────────────────────────────────────

    def _request(self, path: str) -> Any:
        """Executa GET com retry, backoff exponencial, circuit breaker e métricas.

        Se o circuit breaker estiver aberto, retorna dados do cache
        (se disponíveis) ou lista vazia sem fazer requisição.

        Args:
            path: Caminho relativo à base URL (ex: ``/estacoes/T``).

        Returns:
            JSON deserializado ou lista vazia em caso de erro.
        """
        url = f"{self.base_url}{path}"

        # Verifica cache
        cached = self._cache.get(url)
        if cached is not None and cached.is_valid:
            logger.debug("Cache hit: %s", url)
            return cached.data

        # Circuit breaker — se aberto, serve cache expirado ou []
        if self._circuit_breaker.is_open:
            logger.warning(
                "Circuit breaker OPEN — pulando request: %s",
                url,
            )
            INMET_REQUESTS_TOTAL.labels(status="circuit_open").inc()
            # Modo offline: serve cache expirado se disponível
            if cached is not None:
                logger.info("Servindo dados expirados do cache (modo offline): %s", url)
                return cached.data
            return []

        start_time = time.monotonic()
        last_exception: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("INMET request (attempt %d/%d): %s", attempt, self.max_retries, url)
                resp = self._session.get(url, timeout=self.timeout)

                # HTTP 204 — sem dados
                if resp.status_code == 204:
                    elapsed = time.monotonic() - start_time
                    INMET_REQUESTS_TOTAL.labels(status="success").inc()
                    INMET_LATENCY_SECONDS.observe(elapsed)
                    self._circuit_breaker.record_success()
                    logger.info("HTTP 204 (sem dados): %s (%.2fs)", url, elapsed)
                    self._cache[url] = _CacheEntry([], self.cache_ttl)
                    return []

                resp.raise_for_status()
                data = resp.json()

                elapsed = time.monotonic() - start_time
                INMET_REQUESTS_TOTAL.labels(status="success").inc()
                INMET_LATENCY_SECONDS.observe(elapsed)
                self._circuit_breaker.record_success()

                # Armazena no cache
                self._cache[url] = _CacheEntry(data, self.cache_ttl)
                return data

            except requests.exceptions.Timeout as exc:
                last_exception = exc
                logger.warning("Timeout (attempt %d/%d): %s", attempt, self.max_retries, url)
            except requests.exceptions.HTTPError as exc:
                last_exception = exc
                status = exc.response.status_code if exc.response is not None else "?"
                logger.warning(
                    "HTTP %s (attempt %d/%d): %s",
                    status,
                    attempt,
                    self.max_retries,
                    url,
                )
                # Não faz retry para 4xx (exceto 429)
                if (
                    exc.response is not None
                    and 400 <= exc.response.status_code < 500
                    and exc.response.status_code != 429
                ):
                    break
            except requests.exceptions.RequestException as exc:
                last_exception = exc
                logger.warning(
                    "Request error (attempt %d/%d): %s — %s",
                    attempt,
                    self.max_retries,
                    url,
                    exc,
                )

            # Backoff exponencial: 1s, 2s, 4s...
            if attempt < self.max_retries:
                backoff = 2 ** (attempt - 1)
                logger.debug("Backoff %ds antes do retry", backoff)
                time.sleep(backoff)

        elapsed = time.monotonic() - start_time
        INMET_REQUESTS_TOTAL.labels(status="error").inc()
        INMET_LATENCY_SECONDS.observe(elapsed)
        self._circuit_breaker.record_failure()

        logger.error(
            "Todas as tentativas falharam para %s: %s (%.2fs)", url, last_exception, elapsed
        )

        # Modo offline: serve cache expirado se disponível
        if cached is not None:
            logger.info("Servindo dados expirados do cache (fallback): %s", url)
            return cached.data
        return []

    # ── Estações ──────────────────────────────────────────

    def get_stations(self) -> list[dict[str, Any]]:
        """Retorna a lista completa de estações automáticas do INMET.

        Returns:
            Lista de dicionários com dados das estações, ou lista vazia se
            a API estiver indisponível.
        """
        data = self._request("/estacoes/T")
        if not isinstance(data, list):
            logger.warning("Resposta inesperada de /estacoes/T: %s", type(data))
            return []
        return data

    def get_mg_stations(self) -> list[dict[str, Any]]:
        """Retorna apenas estações de Minas Gerais.

        Returns:
            Lista de estações filtradas por ``SG_ESTADO == 'MG'``.
        """
        all_stations = self.get_stations()
        return [s for s in all_stations if s.get("SG_ESTADO") == "MG"]

    def get_priority_stations(self) -> list[dict[str, Any]]:
        """Retorna estações da Zona da Mata e região prioritária.

        Returns:
            Lista de estações cujos códigos estão em ``MG_PRIORITY_STATIONS``.
        """
        all_stations = self.get_stations()
        return [s for s in all_stations if s.get("CD_ESTACAO") in MG_PRIORITY_STATIONS]

    # ── Observações ───────────────────────────────────────

    def get_observations(
        self,
        station_code: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Busca observações horárias de uma estação em um período.

        Args:
            station_code: Código da estação (ex: ``A518``).
            start_date: Data de início (default: ``default_days_back`` dias atrás).
            end_date: Data de fim (default: hoje).

        Returns:
            Lista de observações já normalizadas via ``parse_observation``.
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=self._settings.default_days_back)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        path = f"/estacao/{start_str}/{end_str}/{station_code}"
        raw_data = self._request(path)

        if not isinstance(raw_data, list):
            logger.warning("Resposta inesperada para estação %s: %s", station_code, type(raw_data))
            return []

        return [parse_observation(obs) for obs in raw_data]

    def get_daily_summaries(
        self,
        station_code: str,
        city: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Busca observações e agrega em sumários diários.

        Args:
            station_code: Código da estação INMET.
            city: Nome da cidade.
            start_date: Data de início.
            end_date: Data de fim.

        Returns:
            Lista de sumários diários ordenados por data.
        """
        observations = self.get_observations(station_code, start_date, end_date)
        if not observations:
            return []

        # Coleta datas únicas
        dates: set[str] = set()
        for obs in observations:
            if obs["date"]:
                dates.add(obs["date"])

        summaries = []
        for d in sorted(dates):
            summary = get_daily_summary(observations, city, station_code, d)
            if summary["observation_count"] > 0:
                summaries.append(summary)

        return summaries

    # ── Alertas ───────────────────────────────────────────

    def get_alerts(self, state: str = "MG") -> list[dict[str, Any]]:
        """Busca alertas meteorológicos ativos para um estado.

        Args:
            state: Sigla do estado (default: ``MG``).

        Returns:
            Lista de alertas ou lista vazia se não houver alertas/erro.
        """
        path = "/alertas/ativos"
        data = self._request(path)

        if not isinstance(data, list):
            logger.warning("Resposta inesperada de alertas: %s", type(data))
            return []

        # Filtra alertas do estado desejado
        return [a for a in data if self._alert_matches_state(a, state)]

    @staticmethod
    def _alert_matches_state(alert: dict[str, Any], state: str) -> bool:
        """Verifica se um alerta é do estado informado.

        Args:
            alert: Dicionário do alerta.
            state: Sigla do estado.

        Returns:
            True se o alerta corresponde ao estado.
        """
        alert_state = alert.get("estado", alert.get("uf", alert.get("cod_estado", "")))
        return str(alert_state).upper() == state.upper()

    # ── Utilitários ───────────────────────────────────────

    def clear_cache(self) -> None:
        """Remove todas as entradas do cache em memória."""
        self._cache.clear()
        logger.info("Cache limpo.")

    def get_station_name(self, station_code: str) -> str:
        """Retorna o nome amigável de uma estação.

        Primeiro busca em ``MG_PRIORITY_STATIONS``, depois tenta
        buscar via API.

        Args:
            station_code: Código da estação.

        Returns:
            Nome da cidade ou código da estação se não encontrado.
        """
        if station_code in MG_PRIORITY_STATIONS:
            return MG_PRIORITY_STATIONS[station_code]

        stations = self.get_stations()
        for s in stations:
            if s.get("CD_ESTACAO") == station_code:
                return str(s.get("DC_NOME", station_code))
        return station_code

    def parse_alert(self, raw_alert: dict[str, Any]) -> dict[str, Any]:
        """Normaliza um alerta bruto da API para formato interno.

        Args:
            raw_alert: Alerta conforme retornado pela API.

        Returns:
            Dicionário com campos normalizados.
        """
        inicio_raw = raw_alert.get("inicio", raw_alert.get("dt_inicio", ""))
        fim_raw = raw_alert.get("fim", raw_alert.get("dt_fim", ""))

        return {
            "id": raw_alert.get("id_alerta", raw_alert.get("id", "")),
            "description": raw_alert.get("descricao", ""),
            "severity": raw_alert.get("severidade", ""),
            "start": str(inicio_raw),
            "end": str(fim_raw),
            "event": raw_alert.get("evento", ""),
            "cities": raw_alert.get("municipios", ""),
            "state": raw_alert.get("estado", raw_alert.get("uf", "MG")),
        }
