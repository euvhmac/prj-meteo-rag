# 🌦️ MeteoRAG

> Assistente meteorológico inteligente que combina dados públicos em tempo real do **INMET** com **RAG** (Retrieval-Augmented Generation) e **LLMs** para responder perguntas em linguagem natural sobre chuvas, alertas e condições climáticas em Minas Gerais.

[![CI](https://github.com/user/meteorag/actions/workflows/ci.yml/badge.svg)](https://github.com/user/meteorag/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-261230.svg)](https://github.com/astral-sh/ruff)

---

## 🎯 Sobre

**MeteoRAG** foca na **Zona da Mata mineira** (Juiz de Fora, Ubá, Barbacena, Viçosa) e utiliza:

- **API pública do INMET** — dados horários, alertas e estações automáticas
- **RAG com TF-IDF** — indexação e busca em chunks de dados meteorológicos
- **Claude Haiku 4.5** — geração de respostas em linguagem natural
- **Streamlit** — interface web interativa com chat, gráficos e alertas

---

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- Chave da API Anthropic

### Instalação

```bash
# Clonar o repositório
git clone https://github.com/user/meteorag.git
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
# Rodar testes
pytest tests/unit/ -v

# Verificar linting
ruff check .
black --check .

# Rodar aplicação
streamlit run src/meteorag/ui/app.py
```

### Docker

```bash
docker compose up --build
# Acesse: http://localhost:8501
```

---

## 📁 Estrutura do Projeto

```
meteorag/
├── src/meteorag/           # Código fonte
│   ├── api/                # Cliente API INMET
│   ├── rag/                # Chunker, Retriever, Pipeline
│   ├── llm/                # Cliente LLM (Anthropic)
│   ├── ui/                 # Streamlit app
│   └── config.py           # Configuração via env vars
├── tests/                  # Testes unitários e integração
├── k8s/                    # Manifests Kubernetes
├── helm/                   # Helm Charts
├── monitoring/             # Prometheus + Grafana
├── docs/                   # Documentação
└── .github/                # CI/CD + templates
```

---

## 🧪 Testes

```bash
# Testes unitários com cobertura
pytest tests/unit/ -v --cov=src/meteorag --cov-report=term-missing

# Testes de integração (requer .env configurado)
pytest tests/integration/ -v -m integration
```

---

## 📖 Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Sprints](.github/SPRINTS.md)

---

## ⚠️ Disclaimer

Os dados meteorológicos são obtidos da API pública do INMET e podem conter inconsistências ou indisponibilidades temporárias. Este projeto não substitui os canais oficiais de alerta da Defesa Civil.

---

## 📄 Licença

MIT
