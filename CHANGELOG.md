# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [1.0.0] — 2025-07-12

### Added
- **Chat inteligente** com RAG + LLM (Claude Haiku 4.5) via streaming
- **Open-Meteo** como fonte principal de dados meteorológicos (ERA5 + GFS)
- **Alertas INMET** exibidos com severidade e vigência (best-effort)
- **7 cidades monitoradas**: Juiz de Fora, Ubá, Barbacena, Muriaé, Viçosa, Cataguases, BH
- **TF-IDF Retriever** com cosine similarity (ngram 1-2, max 5000 features)
- **4 tipos de chunk**: daily, hourly, alert, context (≤512 chars)
- **Gráficos Plotly** de precipitação (barras) e temperatura (linhas)
- **Export CSV** dos dados da sessão (tab Dados)
- **Aba "Sobre"** com informações do projeto, fontes e disclaimer
- **Disclaimer** visível sobre dados brutos e limitações dos modelos
- **Métricas Prometheus** (9 métricas: API, LLM, RAG, chat) via porta 8502
- **Dashboard Grafana** com 12 painéis operacionais
- **Circuit breaker** para API INMET (threshold 5, cooldown 5min, cache offline)
- **Logging estruturado** com structlog (JSON em prod, colorido em dev)
- **Kubernetes manifests** completos (deployment, service, ingress, HPA, configmap)
- **Helm Charts** v0.5.0 com templates parametrizados
- **Dockerfile** multi-stage, usuário não-root, health check
- **CI/CD** GitHub Actions (lint + test + build + deploy)
- **Configuração** via pydantic-settings com prefixo `METEORAG_`
- **Testes** com ≥80% de cobertura global (pytest + pytest-cov)
- **Qualidade**: ruff + black + mypy strict
- **Segurança**: bandit + pip-audit sem issues HIGH/CRITICAL
- **Documentação completa**: README, ARCHITECTURE, API_REFERENCE, CHANGELOG

### Sprints

| Sprint | Foco | Commits |
|--------|------|---------|
| Sprint 0 | Scaffold + CI/CD + INMET Client | `be57e65` |
| Sprint 1 | RAG Engine (Chunker + Retriever + Pipeline) | `1b771aa` |
| Sprint 2 | LLM + Streamlit UI + migração Open-Meteo | `2edd85e` |
| Sprint 3 | Kubernetes + Docker + Helm | `27d5a58` |
| Sprint 4 | Monitoramento (Prometheus + Grafana + structlog) | `292739a` |
| Sprint 5 | Qualidade, Documentação e Launch | current |

---

## [0.4.0] — Sprint 4: Monitoramento

### Added
- Prometheus metrics server (porta 8502) com 9 métricas
- Dashboard Grafana com 12 painéis operacionais
- 7 regras de alerta Prometheus (INMET down, LLM latência, CrashLoop)
- structlog para logging estruturado (JSON em produção)
- Circuit breaker para API INMET com cache offline
- Métricas instrumentadas em todos os clients (Open-Meteo, INMET, LLM)

## [0.3.0] — Sprint 3: Kubernetes & Docker

### Added
- Dockerfile multi-stage com usuário não-root
- docker-compose.yml para dev local
- docker-compose.prod.yml para produção
- Kubernetes manifests (namespace, deployment, service, ingress, HPA)
- Helm Charts com values.yaml e values.prod.yaml
- ConfigMap e Secret templates

## [0.2.0] — Sprint 2: LLM & UI

### Added
- Integração com Claude Haiku 4.5 (Anthropic SDK direto)
- Streamlit UI com 3 tabs (Chat, Dados, Debug RAG)
- Streaming de respostas do LLM
- Gráficos Plotly (precipitação e temperatura)
- Cache de dados com @st.cache_data
- Perguntas sugeridas no chat

### Changed
- Migração de INMET para Open-Meteo como fonte principal de dados
- Migração de Databricks para Anthropic SDK direto

## [0.1.0] — Sprint 1: RAG Engine

### Added
- MeteoChunker com 4 tipos de chunk (daily, hourly, alert, context)
- TFIDFRetriever com cosine similarity
- MeteoRAG pipeline completo
- Formatadores de texto (_fmt_rain, _fmt_date_br, etc.)

## [0.0.1] — Sprint 0: Foundation

### Added
- Scaffold inicial do projeto
- INMETClient com retry e cache
- parse_value, parse_observation, get_daily_summary
- Configuração via pydantic-settings
- CI/CD GitHub Actions (lint + test)
- Fixtures de teste abrangentes
