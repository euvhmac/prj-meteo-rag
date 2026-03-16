"""Command-line entry point for the Meteo RAG agent."""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

# Load .env before importing modules that read env vars
load_dotenv()

from src.agents.meteo_agent import MeteoAgent  # noqa: E402
from src.data.inmet import INMETClient  # noqa: E402
from src.data.open_meteo import OpenMeteoClient  # noqa: E402
from src.llm.claude import ClaudeClient  # noqa: E402
from src.rag.retriever import Retriever  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BANNER = """
╔══════════════════════════════════════════════════════════╗
║       Agente Meteorológico Inteligente – Minas Gerais    ║
║       Powered by Open-Meteo, INMET e Claude Haiku        ║
╚══════════════════════════════════════════════════════════╝
Digite sua pergunta sobre clima em MG ou 'sair' para sair.
Digite 'atualizar' para buscar dados meteorológicos novos.
"""


def build_agent() -> MeteoAgent:
    """Instantiate the MeteoAgent with all dependencies."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ERRO: Variável ANTHROPIC_API_KEY não encontrada.\n"
            "Crie um arquivo .env com:\n  ANTHROPIC_API_KEY=sua_chave_aqui\n"
            "Ou exporte a variável no seu shell."
        )
        sys.exit(1)

    return MeteoAgent(
        claude_client=ClaudeClient(api_key=api_key),
        open_meteo_client=OpenMeteoClient(),
        inmet_client=INMETClient(),
        retriever=Retriever(),
    )


def main() -> None:
    """Run the interactive CLI loop."""
    print(BANNER)

    agent = build_agent()

    print("Buscando dados meteorológicos atuais… aguarde.")
    try:
        stats = agent.refresh_data()
        print(
            f"✓ Dados carregados: {stats['cities_loaded']} cidades, "
            f"{stats['alerts_loaded']} alertas INMET.\n"
        )
    except Exception as exc:
        logger.warning("Não foi possível carregar dados: %s", exc)
        print("⚠ Não foi possível carregar dados em tempo real. "
              "As respostas usarão apenas o conhecimento do modelo.\n")

    while True:
        try:
            question = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            break

        if not question:
            continue

        if question.lower() in {"sair", "exit", "quit"}:
            print("Até logo!")
            break

        if question.lower() in {"atualizar", "update", "refresh"}:
            print("Atualizando dados…")
            try:
                stats = agent.refresh_data()
                print(
                    f"✓ Dados atualizados: {stats['cities_loaded']} cidades, "
                    f"{stats['alerts_loaded']} alertas INMET.\n"
                )
            except Exception as exc:
                print(f"⚠ Erro ao atualizar: {exc}\n")
            continue

        try:
            answer = agent.ask(question)
            print(f"\nAgente: {answer}\n")
        except Exception as exc:
            logger.error("Erro ao responder: %s", exc)
            print(f"⚠ Erro ao processar sua pergunta: {exc}\n")


if __name__ == "__main__":
    main()
