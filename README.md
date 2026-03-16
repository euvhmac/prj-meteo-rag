# prj-meteo-rag

Agente meteorológico inteligente que combina dados públicos em tempo real do **Open-Meteo** e alertas do **INMET** com **RAG** (Retrieval-Augmented Generation) e **LLMs** (Claude Haiku) para responder perguntas em linguagem natural sobre chuvas, alertas e condições climáticas em **Minas Gerais**.

## Arquitetura

```
prj-meteo-rag/
├── main.py                   # Ponto de entrada CLI interativo
├── src/
│   ├── agents/
│   │   └── meteo_agent.py    # Orquestrador principal (MeteoAgent)
│   ├── data/
│   │   ├── open_meteo.py     # Cliente Open-Meteo (previsão em tempo real)
│   │   └── inmet.py          # Cliente INMET (alertas meteorológicos)
│   ├── rag/
│   │   ├── document.py       # Modelo de documento RAG
│   │   ├── store.py          # Armazenamento TF-IDF (DocumentStore)
│   │   └── retriever.py      # Recuperação contextual (Retriever)
│   └── llm/
│       └── claude.py         # Integração Claude Haiku (Anthropic)
└── tests/
    ├── test_open_meteo.py
    ├── test_inmet.py
    ├── test_rag.py
    └── test_agent.py
```

### Fluxo do agente

1. **Coleta de dados** – `OpenMeteoClient` busca previsão horária (temperatura, chuva, umidade, vento, código WMO) para 20 cidades de MG; `INMETClient` busca alertas ativos filtrados para MG.
2. **Indexação RAG** – Os resumos em linguagem natural são convertidos em `Document`s e indexados no `DocumentStore` via TF-IDF (scikit-learn).
3. **Recuperação** – O `Retriever` seleciona as passagens mais relevantes para a pergunta do usuário usando similaridade de cosseno.
4. **Geração** – O `ClaudeClient` envia a pergunta + contexto recuperado para o **Claude Haiku** e retorna a resposta em português.

## Pré-requisitos

- Python 3.11+
- Chave de API da Anthropic (Claude Haiku)

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

```bash
cp .env.example .env
# Edite .env e insira sua chave:
# ANTHROPIC_API_KEY=sk-ant-...
```

## Uso (CLI interativo)

```bash
python main.py
```

Exemplo de interação:

```
Você: Está chovendo em Belo Horizonte agora?
Agente: De acordo com os dados mais recentes, Belo Horizonte está registrando chuva leve
        com precipitação de 3,2 mm, temperatura de 22°C e umidade relativa de 78%.

Você: Há algum alerta meteorológico para Minas Gerais?
Agente: Sim, há um alerta INMET nível Amarelo (Atenção) para chuvas intensas em MG,
        válido até as 18h de hoje.

Você: atualizar   ← busca dados novos
Você: sair
```

## Uso como biblioteca

```python
from dotenv import load_dotenv
load_dotenv()

from src.agents.meteo_agent import MeteoAgent
from src.llm.claude import ClaudeClient

agent = MeteoAgent(claude_client=ClaudeClient())
agent.refresh_data()  # busca dados em tempo real

answer = agent.ask("Qual a previsão de chuva para Uberlândia amanhã?")
print(answer)
```

## Cidades cobertas

20 principais municípios de Minas Gerais: Belo Horizonte, Uberlândia, Contagem, Juiz de Fora, Betim, Montes Claros, Ribeirão das Neves, Uberaba, Governador Valadares, Ipatinga, Sete Lagoas, Divinópolis, Teófilo Otoni, Poços de Caldas, Patos de Minas, Coronel Fabriciano, Barbacena, Lavras, Varginha e Itabira.

## Testes

```bash
python -m pytest tests/ -v
```

57 testes unitários cobrindo os clientes de dados, o pipeline RAG e o agente orquestrador (usando mocks para APIs externas).

## Fontes de dados

| Fonte | Descrição | API |
|-------|-----------|-----|
| [Open-Meteo](https://open-meteo.com/) | Previsão meteorológica gratuita | `https://api.open-meteo.com/v1/forecast` |
| [INMET](https://portal.inmet.gov.br/) | Alertas do Instituto Nacional de Meteorologia | `https://apiprevmet3.inmet.gov.br/avisos/ativos` |
| [Anthropic](https://www.anthropic.com/) | LLM Claude Haiku para geração de respostas | API SDK `anthropic` |
