# MeteoRAG — Copilot Instructions

> Instruções canônicas para o agente de desenvolvimento do projeto MeteoRAG.  
> Leia **integralmente** antes de qualquer geração de código.

---

## 1. Identidade do Projeto

**MeteoRAG** é um assistente meteorológico inteligente que combina dados públicos em tempo real do INMET com RAG (Retrieval-Augmented Generation) e LLMs (Claude Haiku 4.5 via Databricks) para responder perguntas em linguagem natural sobre chuvas, alertas e condições climáticas em Minas Gerais.

**Foco geográfico:** Juiz de Fora, Ubá, Barbacena e região da Zona da Mata mineira.  
**Audiência primária:** Cidadãos, pesquisadores, defesa civil e jornalistas.

---

## 2. Stack Tecnológico

| Camada | Tecnologia | Versão Mínima |
|--------|-----------|---------------|
| Frontend / UI | Streamlit | 1.35+ |
| LLM Client | Anthropic SDK | 0.30+ |
| LLM Model | claude-haiku-4-5 | — |
| RAG / Retrieval | TF-IDF custom (sem embedding externo) | — |
| Dados meteorológicos | INMET API REST pública | — |
| Containerização | Docker | 24+ |
| Orquestração | Kubernetes (K8s) | 1.28+ |
| CI/CD | GitHub Actions | — |
| Helm Charts | Helm | 3.14+ |
| Registry | Docker Hub ou GHCR | — |
| Monitoramento | Prometheus + Grafana | — |
| Linguagem | Python | 3.11+ |
| Linter | Ruff | — |
| Formatter | Black | — |
| Type checking | mypy | — |
| Testes | pytest + pytest-cov | — |

---

## 3. Estrutura de Diretórios (canônica)

```
meteorag/
├── .github/
│   ├── copilot-instructions.md     ← este arquivo
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── data_quality.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── ci.yml                  ← lint + test + build
│       ├── cd.yml                  ← push image + deploy k8s
│       └── data-quality.yml        ← verifica API INMET diariamente
├── src/
│   └── meteorag/
│       ├── __init__.py
│       ├── api/
│       │   └── inmet_client.py     ← único ponto de contato com INMET
│       ├── rag/
│       │   ├── chunker.py          ← conversão dados → texto
│       │   ├── retriever.py        ← TF-IDF index + search
│       │   └── pipeline.py         ← orquestra chunking + retrieval
│       ├── llm/
│       │   └── client.py           ← wrapper Anthropic SDK
│       ├── ui/
│       │   └── app.py              ← Streamlit entry point
│       └── config.py               ← settings via pydantic-settings
├── tests/
│   ├── unit/
│   │   ├── test_chunker.py
│   │   ├── test_retriever.py
│   │   └── test_inmet_client.py
│   ├── integration/
│   │   └── test_rag_pipeline.py
│   └── conftest.py
├── k8s/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secret.yaml                 ← template (valores via CI/CD)
│   └── hpa.yaml
├── helm/
│   └── meteorag/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values.prod.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── ingress.yaml
│           ├── configmap.yaml
│           └── hpa.yaml
├── monitoring/
│   ├── prometheus/
│   │   └── rules.yaml
│   └── grafana/
│       └── dashboard.json
├── scripts/
│   ├── seed_data.py                ← popula cache inicial de dados INMET
│   └── health_check.py
├── docs/
│   ├── SPRINTS.md
│   ├── API_REFERENCE.md
│   └── ARCHITECTURE.md
├── Dockerfile
├── docker-compose.yml              ← dev local
├── docker-compose.prod.yml
├── pyproject.toml                  ← black, ruff, mypy, pytest config
├── requirements.txt                ← produção
├── requirements-dev.txt            ← testes + linting
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

---

## 4. Padrões de Código

### 4.1 Estilo Geral
- **Python 3.11+** com type hints em TODAS as funções públicas
- **Black** para formatação (line-length = 100)
- **Ruff** para linting (`ruff check .`)
- **mypy** em modo strict para módulos `src/meteorag/`
- Docstrings: estilo **Google** em todas as classes e funções públicas
- Nomes em **inglês** para código; comentários podem ser em PT-BR

### 4.2 Configuração
- **Toda configuração via variáveis de ambiente** usando `pydantic-settings`
- Nunca hardcode API keys, URLs ou parâmetros no código
- Arquivo `.env.example` sempre atualizado com todas as vars necessárias
- Seguir o padrão `METEORAG_*` para vars do projeto

### 4.3 Módulo INMET Client
- **Todo acesso à API INMET passa por `src/meteorag/api/inmet_client.py`**
- Implementar retry com backoff exponencial (max 3 tentativas)
- Cache em memória com TTL de 30 minutos por padrão
- Tratar explicitamente: HTTP 204 (sem dados), HTTP 503 (API fora), timeouts
- Valores inválidos `9999`, `-9999`, `null` ou `""` devem retornar `None`
- Nunca propagar exceções da API para a UI — retornar lista vazia com log

### 4.4 RAG Engine
- **Chunking é determinístico**: mesma entrada → mesmo chunk
- Chunks devem ter máximo de 512 caracteres
- Sempre incluir metadados: `city`, `date`, `type` (hourly | daily | alert | context)
- TF-IDF index rebuilda completamente ao adicionar nova cidade (não incremental)
- Retrieval retorna no mínimo score > 0 ou lista vazia (nunca retorna chunk irrelevante)

### 4.5 LLM Client
- Sempre usar `claude-haiku-4-5` como model padrão
- System prompt define persona e contexto — nunca alterar inline
- Histórico de chat limitado a **últimas 10 mensagens** para controle de tokens
- Timeout de 30s na chamada ao LLM
- Em caso de erro do LLM, retornar mensagem de fallback — nunca crash na UI

### 4.6 Streamlit UI
- **Nunca usar `st.experimental_*`** (deprecated)
- Estado global exclusivamente via `st.session_state`
- Cache de dados com `@st.cache_data(ttl=1800)`
- Sidebar para configuração; main para conteúdo
- Spinner + mensagens de progresso em toda operação longa
- Tratar caso de dados vazios/indisponíveis com mensagem útil ao usuário

---

## 5. Git Workflow

### Branch Strategy
```
main          ← produção — protegida, requer PR + review
develop       ← integração — branch base para features
feature/*     ← novas features (ex: feature/S1-inmet-client)
fix/*         ← correções (ex: fix/S2-alert-parsing)
hotfix/*      ← correções urgentes em produção
chore/*       ← infra, deps, docs (ex: chore/S3-k8s-ingress)
```

### Convenção de Commits (Conventional Commits)
```
feat(rag): add TF-IDF retriever with cosine scoring
fix(inmet): handle HTTP 204 for stations with no data
chore(k8s): add HPA config for streamlit deployment
docs(api): add INMET endpoint reference for alerts
test(chunker): add unit tests for daily summary chunk
ci(github-actions): add ruff linting step to CI pipeline
refactor(llm): extract system prompt to separate constant
perf(retriever): cache tokenized documents between queries
```

### PR Rules
- PR description deve referenciar a Sprint e issue: `Closes #42 | Sprint 2`
- Requer ao menos 1 approval
- CI deve passar (lint + tests + build) antes de merge
- Squash merge para features; merge commit para releases

---

## 6. Variáveis de Ambiente

```bash
# ── LLM ─────────────────────────────────────────────────
METEORAG_ANTHROPIC_API_KEY=        # obrigatório
METEORAG_ANTHROPIC_BASE_URL=       # opcional (Databricks)
METEORAG_LLM_MODEL=claude-haiku-4-5
METEORAG_LLM_MAX_TOKENS=1024
METEORAG_LLM_TIMEOUT_SECONDS=30

# ── INMET ────────────────────────────────────────────────
METEORAG_INMET_BASE_URL=https://apitempo.inmet.gov.br
METEORAG_INMET_CACHE_TTL_SECONDS=1800
METEORAG_INMET_RETRY_MAX=3
METEORAG_INMET_TIMEOUT_SECONDS=20
METEORAG_DEFAULT_DAYS_BACK=7

# ── RAG ──────────────────────────────────────────────────
METEORAG_RAG_TOP_K=8
METEORAG_RAG_MAX_CHUNK_SIZE=512
METEORAG_RAG_MAX_HOURLY_CHUNKS=96

# ── APP ──────────────────────────────────────────────────
METEORAG_APP_PORT=8501
METEORAG_LOG_LEVEL=INFO
METEORAG_ENVIRONMENT=production    # development | production
```

---

## 7. Testes

### Cobertura mínima por módulo
| Módulo | Cobertura Mínima |
|--------|-----------------|
| `inmet_client.py` | 85% |
| `chunker.py` | 90% |
| `retriever.py` | 90% |
| `pipeline.py` | 80% |
| `llm/client.py` | 70% |
| Global | 80% |

### Regras
- **Sem mocks da API INMET em testes unitários** — usar fixtures com dados reais anonimizados
- Testes de integração marcados com `@pytest.mark.integration` e pulados no CI padrão
- Todo bug fixado deve ter um teste de regressão
- Fixtures em `conftest.py` — nunca duplicar dados de teste

### Rodando testes
```bash
pytest tests/unit/ -v --cov=src/meteorag --cov-report=term-missing
pytest tests/integration/ -v -m integration   # requer .env configurado
```

---

## 8. Docker & Kubernetes

### Dockerfile Rules
- Base image: `python:3.11-slim` (não usar `latest`)
- Multi-stage build obrigatório (builder + runtime)
- Usuário não-root: `USER meteorag`
- Health check: `HEALTHCHECK --interval=30s CMD curl -f http://localhost:8501/_stcore/health`
- `.dockerignore` deve excluir: `.git`, `tests/`, `docs/`, `*.md`, `__pycache__`

### Kubernetes Rules
- Namespace dedicado: `meteorag`
- Resource limits obrigatórios em todos os containers
- Liveness + Readiness probes em todos os deployments
- Secrets nunca em plain text no repo — usar Kubernetes Secrets (populados via CI/CD)
- HPA configurado: min 1, max 3 réplicas baseado em CPU (70%)
- ConfigMap para configs não-sensíveis

### Helm Rules
- `values.yaml` contém defaults seguros (sem secrets)
- `values.prod.yaml` sobrescreve para produção (sem secrets também)
- Secrets injetados via `--set` no deploy ou via Sealed Secrets

---

## 9. Monitoramento

### Métricas customizadas (Prometheus)
- `meteorag_inmet_requests_total` — counter por status (success/error)
- `meteorag_inmet_latency_seconds` — histogram de latência da API INMET
- `meteorag_llm_requests_total` — counter por status
- `meteorag_llm_latency_seconds` — histogram de latência do LLM
- `meteorag_rag_chunks_total` — gauge do total de chunks indexados
- `meteorag_chat_messages_total` — counter de mensagens processadas

### Alertas (regras Prometheus)
- API INMET indisponível por > 5 min → alerta WARNING
- LLM latência p95 > 10s → alerta WARNING
- Pod em CrashLoopBackOff → alerta CRITICAL

---

## 10. O que NÃO fazer

- ❌ Nunca commitar `.env` ou qualquer arquivo com credenciais
- ❌ Nunca usar `print()` em produção — usar `logging`
- ❌ Nunca fazer requisição HTTP na thread principal do Streamlit sem spinner
- ❌ Nunca alterar o system prompt do LLM inline na UI
- ❌ Nunca retornar dados raw da API INMET diretamente para a UI
- ❌ Nunca usar `time.sleep()` no código principal — usar async quando necessário
- ❌ Nunca ignorar o tipo de retorno `-9999` / `9999` da API INMET
- ❌ Nunca fazer rebuild do TF-IDF index a cada query — apenas ao indexar
- ❌ Nunca subir imagem Docker com tag `latest` para produção
- ❌ Nunca usar `st.experimental_rerun()` (deprecated)

---

## 11. Referências Rápidas

| Recurso | URL |
|---------|-----|
| API INMET Estações | `https://apitempo.inmet.gov.br/estacoes/T` |
| API INMET Dados | `https://apitempo.inmet.gov.br/estacao/{start}/{end}/{id}` |
| API INMET Alertas | `https://apitempo.inmet.gov.br/alertas/{estado}/1` |
| Portal INMET | https://portal.inmet.gov.br |
| Alertas INMET | https://alertas2.inmet.gov.br |
| Docs Anthropic | https://docs.anthropic.com |
| Sprints | `docs/SPRINTS.md` |
| API Reference | `docs/API_REFERENCE.md` |
