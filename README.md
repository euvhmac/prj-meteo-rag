# 🌦️ MeteoRAG

> Assistente meteorológico inteligente que combina dados públicos em tempo real com **RAG** (Retrieval-Augmented Generation) e **LLMs** para responder perguntas em linguagem natural sobre condições climáticas em Minas Gerais — com foco em **prevenção de desastres** na Zona da Mata mineira.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![Coverage ≥80%](https://img.shields.io/badge/coverage-%E2%89%A580%25-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 O Problema

Minas Gerais — em especial a Zona da Mata — sofre recorrentemente com enchentes, deslizamentos e eventos climáticos severos. A informação meteorológica existe (INMET, Open-Meteo, Defesa Civil), mas é **fragmentada**, **técnica** e muitas vezes **chega tarde** para o cidadão comum.

O MeteoRAG nasceu para resolver isso: transformar dados meteorológicos brutos em **respostas acessíveis e contextualizadas** usando IA generativa.

## 💡 A Solução

O MeteoRAG combina três camadas:

1. **Dados em tempo real** — coleta automática via Open-Meteo (previsão + histórico) e INMET (alertas oficiais)
2. **RAG (Retrieval-Augmented Generation)** — indexa os dados meteorológicos como chunks de texto e busca os mais relevantes para cada pergunta
3. **LLM (Claude Haiku)** — interpreta os dados e responde em linguagem natural, com contexto local

O resultado: o usuário pergunta *"vai chover forte em Juiz de Fora?"* e recebe uma resposta que considera a previsão atual, dados recentes e alertas ativos — tudo em português, sem precisar interpretar tabelas ou códigos meteorológicos.

---

## ✨ Funcionalidades

| Feature | Descrição |
|---------|-----------|
| 💬 **Chat inteligente** | Perguntas em linguagem natural sobre clima com respostas contextualizadas |
| 📊 **Visualizações** | Gráficos interativos de precipitação e temperatura (Plotly) |
| ⚠️ **Alertas INMET** | Alertas meteorológicos ativos com severidade e cidades afetadas |
| 🔍 **Debug RAG** | Inspeção de chunks, scores TF-IDF e contexto enviado ao LLM |
| 📥 **Export CSV** | Download dos dados meteorológicos da sessão |
| 🏗️ **Observabilidade** | Métricas Prometheus + dashboard Grafana |
| 🔄 **Circuit Breaker** | Resiliência com fallback para cache quando APIs ficam indisponíveis |
| 📝 **Logging estruturado** | structlog com JSON (produção) e output colorido (desenvolvimento) |

---

## 🏗️ Arquitetura

```
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌───────────┐
│  Usuário │────▸│ Streamlit │────▸│   RAG    │────▸│   LLM     │
│  (Chat)  │◂────│    UI     │◂────│ Pipeline │◂────│  (Claude) │
└──────────┘     └─────┬─────┘     └────┬─────┘     └───────────┘
                       │                │
              ┌────────┴────────┐  ┌────┴─────┐
              │  Prometheus     │  │Open-Meteo│ (fonte principal)
              │  :8502/metrics  │  └──────────┘
              └─────────────────┘  ┌──────────┐
                                   │  INMET   │ (alertas)
                                   └──────────┘
```

### Stack técnico

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Streamlit |
| LLM | Claude Haiku 4.5 (Anthropic SDK) |
| RAG | TF-IDF + Cosine Similarity (scikit-learn) |
| Dados | Open-Meteo API + INMET API |
| Monitoramento | Prometheus + Grafana |
| Infraestrutura | Docker + Kubernetes + Helm |
| CI/CD | GitHub Actions |
| Qualidade | pytest (87%+ cov), ruff, black, mypy strict |

Para detalhes completos, veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- Chave da API Anthropic (obrigatório para o chat com LLM)

### Instalação

```bash
git clone https://github.com/euvhmac/prj-meteo-rag.git
cd prj-meteo-rag

python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -r requirements-dev.txt

cp .env.example .env
# Editar .env com sua METEORAG_ANTHROPIC_API_KEY
```

### Executar

```bash
streamlit run src/meteorag/ui/app.py
# Acesse: http://localhost:8501
```

### Docker

```bash
# Desenvolvimento
docker compose up --build

# Produção
docker compose -f docker-compose.prod.yml up -d
```

---

## 🧪 Testes

```bash
# Unitários com cobertura
pytest tests/unit/ -v --cov=src/meteorag --cov-report=term-missing

# Integração (requer .env)
pytest tests/integration/ -v -m integration

# Lint completo
ruff check . && black --check . && mypy src/meteorag/
```

| Métrica | Status |
|---------|--------|
| Cobertura global | ≥ 80% (87.20%) |
| ruff | ✅ clean |
| black | ✅ formatted |
| mypy (strict) | ✅ clean |
| bandit | ✅ sem HIGH/CRITICAL |

---

## 📁 Estrutura do Projeto

```
prj-meteo-rag/
├── src/meteorag/
│   ├── api/                   # Clientes de APIs externas
│   │   ├── openmeteo_client.py
│   │   └── inmet_client.py
│   ├── rag/                   # Engine RAG
│   │   ├── chunker.py         # Dados → chunks de texto
│   │   ├── retriever.py       # TF-IDF + cosine similarity
│   │   └── pipeline.py        # Orquestração completa
│   ├── llm/
│   │   └── client.py          # Wrapper Anthropic SDK
│   ├── ui/
│   │   └── app.py             # Interface Streamlit
│   ├── config.py              # pydantic-settings
│   ├── metrics.py             # Prometheus
│   └── logging.py             # structlog
├── tests/                     # 260 testes (unit + integration)
├── k8s/                       # Kubernetes manifests
├── helm/meteorag/             # Helm Charts
├── monitoring/                # Prometheus rules + Grafana dashboard
├── docs/                      # Arquitetura, API Reference, Sprints
├── Dockerfile                 # Multi-stage, non-root
├── docker-compose.yml
└── CHANGELOG.md
```

---

## ⚙️ Configuração

Todas as variáveis usam o prefixo `METEORAG_`. Veja [.env.example](.env.example).

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `METEORAG_ANTHROPIC_API_KEY` | ✅ | Chave da API Anthropic |
| `METEORAG_LLM_MODEL` | | Modelo LLM (default: `claude-haiku-4-5-20251001`) |
| `METEORAG_DEFAULT_DAYS_BACK` | | Dias retroativos (default: 7) |
| `METEORAG_RAG_TOP_K` | | Chunks retornados por busca (default: 8) |
| `METEORAG_LOG_LEVEL` | | Nível de log (default: INFO) |
| `METEORAG_ENVIRONMENT` | | `development` ou `production` |

---

## 🔮 Próximos Passos

Este repositório é a **fundação open-source** do MeteoRAG. O projeto continua evoluindo com foco em:

- 📦 **Dados próprios** — armazenamento local com banco analítico para análise histórica de 5+ anos
- 📊 **Análise de risco** — score de risco por cidade baseado em padrões históricos de chuva
- 🤖 **Alertas proativos** — notificações automáticas quando condições de risco são detectadas
- 🌐 **API REST pública** — para que outros projetos possam consumir os dados processados

Acompanhe o progresso no [CHANGELOG](CHANGELOG.md).

---

## 📖 Documentação

- [Arquitetura e ADRs](docs/ARCHITECTURE.md)
- [Referência de APIs](docs/API_REFERENCE.md)
- [Planejamento de Sprints](docs/SPRINTS.md)
- [Changelog](CHANGELOG.md)

---

## 🤝 Contribuindo

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/minha-feature`)
3. Siga os padrões: **Black** (line-length 100), **Ruff**, **mypy strict**
4. Adicione testes para novas funcionalidades
5. Faça commit seguindo [Conventional Commits](https://www.conventionalcommits.org/)
6. Abra um Pull Request

---

## ⚠️ Disclaimer

Os dados meteorológicos são obtidos da API pública **Open-Meteo** (modelos ERA5/GFS) e os alertas da API pública do **INMET**. Os dados podem ter atraso ou imprecisões inerentes aos modelos numéricos. **Este projeto não substitui os canais oficiais de alerta da Defesa Civil.** Para emergências, consulte [alertas2.inmet.gov.br](https://alertas2.inmet.gov.br).

---

## 📄 Licença

MIT © [Victor Hugo](https://github.com/euvhmac)