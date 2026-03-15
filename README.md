# 🌦️ MeteoRAG

> Assistente meteorológico inteligente que combina dados públicos em tempo real do **Open-Meteo** e alertas do **INMET** com **RAG** (Retrieval-Augmented Generation) e **LLMs** (Claude Haiku) para responder perguntas em linguagem natural sobre chuvas, alertas e condições climáticas em Minas Gerais.

[![CI](https://github.com/victorliquiddata/meteorag/actions/workflows/ci.yml/badge.svg)](https://github.com/victorliquiddata/meteorag/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![Coverage ≥80%](https://img.shields.io/badge/coverage-%E2%89%A580%25-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 Sobre

**MeteoRAG** foca na **Zona da Mata mineira** (Juiz de Fora, Ubá, Barbacena, Viçosa, Muriaé, Cataguases) e utiliza:

- **Open-Meteo API** — fonte principal de dados meteorológicos (reanálise ERA5 + previsão GFS)
- **INMET API** — alertas meteorológicos ativos (best-effort)
- **RAG com TF-IDF** — indexação e busca em chunks de dados meteorológicos
- **Claude Haiku 4.5** (Anthropic) — geração de respostas em linguagem natural
- **Streamlit** — interface web interativa com chat, gráficos e alertas
- **Prometheus + Grafana** — monitoramento de métricas e alertas operacionais
- **Kubernetes + Helm** — orquestração e deploy em produção

### Funcionalidades

| Feature | Descrição |
|---------|-----------|
| 💬 **Chat inteligente** | Perguntas em linguagem natural sobre clima com respostas contextualizadas |
| 📊 **Visualizações** | Gráficos de precipitação e temperatura com Plotly |
| ⚠️ **Alertas INMET** | Exibição de alertas meteorológicos ativos com severidade |
| 🔍 **Debug RAG** | Aba para inspecionar chunks e scores do TF-IDF |
| 📥 **Export CSV** | Download dos dados da sessão em formato CSV |
| 🏗️ **Observabilidade** | Métricas Prometheus + dashboard Grafana com 12 painéis |
| 🔄 **Circuit Breaker** | Resiliência para API INMET com fallback para cache |
| 📝 **Logging estruturado** | structlog com JSON em produção, colorido em dev |

---

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- Chave da API Anthropic (obrigatório para chat)

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/victorliquiddata/meteorag.git
cd meteorag

# Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependências
pip install -r requirements-dev.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com sua METEORAG_ANTHROPIC_API_KEY
```

### Executar

```bash
# Rodar aplicação
streamlit run src/meteorag/ui/app.py

# Acesse: http://localhost:8501
```

### Docker

```bash
# Desenvolvimento
docker compose up --build

# Produção
docker compose -f docker-compose.prod.yml up -d

# Acesse: http://localhost:8501
```

---

## 🧪 Testes & Qualidade

```bash
# Testes unitários com cobertura
pytest tests/unit/ -v --cov=src/meteorag --cov-report=term-missing

# Testes de integração (requer .env configurado)
pytest tests/integration/ -v -m integration

# Linting & Formatting
ruff check .
black --check .
mypy src/meteorag/

# Auditoria de segurança
bandit -r src/meteorag/ -c pyproject.toml
pip-audit
```

| Métrica | Status |
|---------|--------|
| Cobertura global | ≥ 80% |
| ruff | ✅ clean |
| black | ✅ formatted |
| mypy (strict) | ✅ clean |
| bandit | ✅ sem HIGH/CRITICAL |

---

## 📁 Estrutura do Projeto

```
meteorag/
├── src/meteorag/              # Código fonte
│   ├── api/
│   │   ├── inmet_client.py    # Cliente INMET (alertas + circuit breaker)
│   │   └── openmeteo_client.py # Cliente Open-Meteo (dados meteorológicos)
│   ├── rag/
│   │   ├── chunker.py         # Conversão dados → chunks de texto
│   │   ├── retriever.py       # TF-IDF index + cosine similarity
│   │   └── pipeline.py        # Orquestração RAG completa
│   ├── llm/
│   │   └── client.py          # Wrapper Anthropic SDK + streaming
│   ├── ui/
│   │   └── app.py             # Streamlit (chat, dados, debug, sobre)
│   ├── config.py              # Configuração via pydantic-settings
│   ├── metrics.py             # Métricas Prometheus (9 métricas)
│   └── logging.py             # Logging estruturado (structlog)
├── tests/
│   ├── unit/                  # Testes unitários (sem I/O)
│   ├── integration/           # Testes de integração RAG→LLM
│   └── conftest.py            # Fixtures compartilhadas
├── k8s/                       # Manifests Kubernetes
├── helm/meteorag/             # Helm Charts
├── monitoring/
│   ├── prometheus/rules.yaml  # 7 regras de alerta
│   └── grafana/dashboard.json # Dashboard operacional (12 painéis)
├── docs/
│   ├── ARCHITECTURE.md        # Arquitetura e ADRs
│   ├── API_REFERENCE.md       # Referência de APIs externas
│   └── SPRINTS.md             # Planejamento de sprints
├── Dockerfile                 # Multi-stage build, não-root
├── docker-compose.yml         # Dev local
├── pyproject.toml             # Configuração de ferramentas
├── requirements.txt           # Deps de produção
├── requirements-dev.txt       # Deps de desenvolvimento
├── CHANGELOG.md               # Histórico de versões
└── .env.example               # Template de variáveis de ambiente
```

---

## ⚙️ Configuração

Todas as variáveis usam o prefixo `METEORAG_`. Veja [.env.example](.env.example) para a lista completa.

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `METEORAG_ANTHROPIC_API_KEY` | ✅ | Chave da API Anthropic |
| `METEORAG_LLM_MODEL` | | Modelo LLM (default: `claude-haiku-4-5-20251001`) |
| `METEORAG_DEFAULT_DAYS_BACK` | | Dias retroativos (default: 7) |
| `METEORAG_RAG_TOP_K` | | Chunks retornados (default: 8) |
| `METEORAG_LOG_LEVEL` | | Nível de log (default: INFO) |
| `METEORAG_ENVIRONMENT` | | `development` ou `production` |

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
                                   │  INMET   │ (alertas best-effort)
                                   └──────────┘
```

Para detalhes, veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 📖 Documentação

- [Arquitetura e ADRs](docs/ARCHITECTURE.md)
- [Referência de APIs externas](docs/API_REFERENCE.md)
- [Planejamento de Sprints](docs/SPRINTS.md)
- [Changelog](CHANGELOG.md)

---

## 🤝 Contribuindo

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/minha-feature`)
3. Siga os padrões: **Black** (line-length 100), **Ruff**, **mypy strict**
4. Adicione testes para novas funcionalidades
5. Faça commit seguindo [Conventional Commits](https://www.conventionalcommits.org/)
6. Abra um Pull Request para `develop`

---

## ⚠️ Disclaimer

Os dados meteorológicos são obtidos da API pública **Open-Meteo** (modelos ERA5/GFS) e os alertas da API pública do **INMET**. Os dados podem ter atraso ou imprecisões inerentes aos modelos numéricos. **Este projeto não substitui os canais oficiais de alerta da Defesa Civil.** Para emergências, consulte [alertas2.inmet.gov.br](https://alertas2.inmet.gov.br).

---

## 📄 Licença

MIT
