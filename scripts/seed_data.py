"""Script para popular cache inicial de dados meteorológicos.

Indexa as cidades prioritárias de MG no pipeline RAG,
preparando os chunks TF-IDF antes da primeira query do usuário.

Uso:
    python scripts/seed_data.py [--days DAYS] [--cities CITIES]

Exemplos:
    python scripts/seed_data.py
    python scripts/seed_data.py --days 14
    python scripts/seed_data.py --cities "Juiz de Fora,Barbacena"
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

# Configura path para importar meteorag
sys.path.insert(0, "src")

from meteorag.api.openmeteo_client import MG_CITIES
from meteorag.config import get_settings
from meteorag.rag.pipeline import MeteoRAG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def seed(cities: list[str], days_back: int) -> None:
    """Indexa cidades no pipeline RAG.

    Args:
        cities: Lista de nomes de cidades para indexar.
        days_back: Número de dias retroativos para buscar dados.
    """
    settings = get_settings()
    rag = MeteoRAG(settings=settings)

    total_chunks = 0
    start = time.time()

    for city in cities:
        if city not in MG_CITIES:
            logger.warning("Cidade '%s' não encontrada em MG_CITIES — ignorando.", city)
            continue

        logger.info("Indexando %s (%d dias)...", city, days_back)
        try:
            chunks = rag.index_city(city, days_back=days_back)
            total_chunks += chunks
            logger.info("  → %d chunks indexados para %s", chunks, city)
        except Exception:
            logger.exception("Erro ao indexar %s", city)

    elapsed = time.time() - start
    logger.info(
        "Seed concluído: %d chunks de %d cidades em %.1fs",
        total_chunks,
        len(cities),
        elapsed,
    )


def main() -> None:
    """Ponto de entrada do seed script."""
    available = list(MG_CITIES.keys())

    parser = argparse.ArgumentParser(description="MeteoRAG — Seed Data")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Dias retroativos para buscar (default: 7)",
    )
    parser.add_argument(
        "--cities",
        type=str,
        default="",
        help=f"Cidades separadas por vírgula (default: todas). Disponíveis: {available}",
    )
    args = parser.parse_args()

    cities = [c.strip() for c in args.cities.split(",") if c.strip()] if args.cities else available

    logger.info("🌱 Iniciando seed de dados MeteoRAG")
    logger.info("   Cidades: %s", ", ".join(cities))
    logger.info("   Dias: %d", args.days)
    print()

    seed(cities, args.days)


if __name__ == "__main__":
    main()
