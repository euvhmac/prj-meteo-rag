"""Health check script para validação pós-deploy.

Verifica se o MeteoRAG está respondendo corretamente.

Uso:
    python scripts/health_check.py [--url URL] [--timeout SECONDS]

Retorna:
    exit 0 — app saudável
    exit 1 — app não responde ou com erro
"""

from __future__ import annotations

import argparse
import sys
import time

import requests  # type: ignore[import-untyped]

DEFAULT_URL = "http://localhost:8501/_stcore/health"
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 5


def check_health(url: str, timeout: int) -> bool:
    """Verifica se o endpoint de saúde está respondendo.

    Args:
        url: URL do health check endpoint.
        timeout: Timeout em segundos para a requisição.

    Returns:
        True se o app está saudável, False caso contrário.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                print(f"✅ Health check OK — {url} (HTTP {response.status_code})")
                return True
            print(
                f"⚠️  Tentativa {attempt}/{MAX_RETRIES} — " f"HTTP {response.status_code} em {url}"
            )
        except requests.ConnectionError:
            print(f"⚠️  Tentativa {attempt}/{MAX_RETRIES} — " f"Conexão recusada em {url}")
        except requests.Timeout:
            print(f"⚠️  Tentativa {attempt}/{MAX_RETRIES} — " f"Timeout ({timeout}s) em {url}")
        except requests.RequestException as exc:
            print(f"⚠️  Tentativa {attempt}/{MAX_RETRIES} — Erro: {exc}")

        if attempt < MAX_RETRIES:
            print(f"   Aguardando {RETRY_DELAY}s antes de tentar novamente...")
            time.sleep(RETRY_DELAY)

    return False


def main() -> None:
    """Ponto de entrada do health check."""
    parser = argparse.ArgumentParser(description="MeteoRAG Health Check")
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"URL do endpoint de saúde (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout em segundos (default: {DEFAULT_TIMEOUT})",
    )
    args = parser.parse_args()

    print(f"🔍 Verificando saúde do MeteoRAG em {args.url}...")
    print(f"   Timeout: {args.timeout}s | Retries: {MAX_RETRIES}")
    print()

    is_healthy = check_health(args.url, args.timeout)

    if is_healthy:
        print("\n🎉 MeteoRAG está saudável!")
        sys.exit(0)
    else:
        print(f"\n❌ MeteoRAG não respondeu após {MAX_RETRIES} tentativas.")
        sys.exit(1)


if __name__ == "__main__":
    main()
