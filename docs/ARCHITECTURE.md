# MeteoRAG — Arquitetura

> Documento de decisões arquiteturais e visão técnica do projeto.

---

## Visão Geral

MeteoRAG é um assistente meteorológico RAG (Retrieval-Augmented Generation) que
combina dados em tempo real com um LLM para responder perguntas em linguagem natural.

---

## Diagrama de Fluxo (Alto Nível)

```
                           ┌─────────────────────────────────┐
                           │         Streamlit UI             │
                           │  (Chat · Dados · Debug · Sobre)  │
                           └────────┬──────────┬──────────────┘
                                    │          │
                          ┌─────────▼──┐  ┌────▼──────────┐
                          │  RAG       │  │  Prometheus    │
                          │  Pipeline  │  │  :8502/metrics │
                          └──┬──┬──┬───┘  └───────────────┘
                             │  │  │
                ┌────────────┘  │  └────────────┐
                │               │               │
        ┌───────▼───────┐ ┌────▼─────┐  ┌──────▼──────┐
        │  Open-Meteo   │ │  INMET   │  │    LLM      │
        │  Client       │ │  Client  │  │  (Claude    │
        │  (principal)  │ │  (alerts)│  │   Haiku)    │
        └───────┬───────┘ └────┬─────┘  └─────────────┘
                │              │
        ┌───────▼───────┐ ┌───▼──────────┐
        │  MeteoChunker │ │  Circuit     │
        │  (4 tipos)    │ │  Breaker     │
        └───────┬───────┘ └──────────────┘
                │
        ┌───────▼───────┐
        │  TF-IDF       │
        │  Retriever    │
        └───────────────┘
```

---

## Fluxo de Dados

```
1. Usuário seleciona cidades na sidebar → clica "Carregar Dados"
2. Para cada cidade:
   a. OpenMeteoClient.get_weather() → dados hourly + daily + current
   b. INMETClient.get_alerts("MG") → alertas ativos (best-effort)
3. MeteoChunker.chunk_all() gera 4 tipos de chunk:
   - daily   : resumo diário (chuva, temp, umidade, condição WMO)
   - hourly  : observações com chuva > 0 ou vento > 10 m/s
   - alert   : alertas INMET com severidade e vigência
   - context : contexto semanal agregado
4. TFIDFRetriever.index() constrói índice TF-IDF (rebuild completo)
5. Usuário faz pergunta no chat
6. Pipeline.get_context_for_llm() busca chunks relevantes (cosine similarity)
7. LLM Client envia: system prompt + histórico + [contexto RAG + pergunta]
8. Resposta via streaming exibida no chat
```

---

## Componentes

### API Clients

| Client | Fonte | Uso | Resiliência |
|--------|-------|-----|-------------|
| `OpenMeteoClient` | api.open-meteo.com | Dados hourly/daily/current | Cache TTL 30min |
| `INMETClient` | apitempo.inmet.gov.br | Alertas ativos | Circuit breaker + retry 3× + cache offline |

### RAG Engine

- **Chunker**: Gera chunks ≤512 chars com metadata (`city`, `date`, `type`)
- **Retriever**: TF-IDF com `TfidfVectorizer` (ngram 1-2, sublinear TF, max 5000 features)
- **Pipeline**: Orquestra indexação (multi-cidade) e retrieval com filtros

### LLM

- **Model**: `claude-haiku-4-5-20251001` via Anthropic SDK
- **System Prompt**: Persona MeteoRAG com regras de interpretação numérica e códigos WMO
- **Histórico**: Limitado a 10 mensagens, sempre começando com `user`
- **Streaming**: `ask_stream()` via generator para UI responsiva

### Observabilidade

- **Métricas Prometheus** (9 métricas): counters, histograms e gauges
- **Dashboard Grafana**: 12 painéis operacionais
- **Logging estruturado**: structlog com JSON (prod) ou colorido (dev)
- **Alertas**: 7 regras Prometheus (INMET down, LLM latência, CrashLoop)

---

## Decisões Técnicas (ADRs)

### ADR-001: TF-IDF ao invés de embeddings semânticos
- **Status:** Aceito
- **Contexto:** Precisávamos de um motor de busca para chunks meteorológicos
- **Decisão:** Usar TF-IDF (scikit-learn) ao invés de embeddings (OpenAI, Sentence-Transformers)
- **Motivo:** Menor dependência externa, menor custo computacional, sem necessidade de GPU.
  Suficiente para domínio restrito (meteorologia MG) com vocabulário limitado.
- **Trade-off:** Menor recall semântico, compensado por chunking contextual rico
  que inclui sinônimos naturais (ex: "chuva forte de 45mm").

### ADR-002: Open-Meteo como fonte principal (migração de INMET)
- **Status:** Aceito (Sprint 2)
- **Contexto:** API INMET apresentava instabilidade crônica (503, timeouts, dados incompletos).
  Dados de estações automáticas tinham gaps frequentes.
- **Decisão:** Migrar para Open-Meteo (reanálise ERA5 + previsão GFS) como fonte principal.
  INMET mantido apenas para alertas meteorológicos (best-effort).
- **Motivo:** Open-Meteo é gratuita, sem autenticação, com uptime superior e dados globais.
  ERA5 fornece dados históricos consistentes; GFS fornece previsão.
- **Trade-off:** Dados vêm de modelo numérico, não de estação física local.

### ADR-003: Circuit Breaker para API INMET
- **Status:** Aceito (Sprint 4)
- **Contexto:** API INMET frequentemente retorna 503 ou timeout, causando
  latência acumulada devido a retries sequenciais.
- **Decisão:** Implementar circuit breaker com 3 estados (closed/open/half-open),
  threshold de 5 falhas, cooldown de 5 minutos.
- **Motivo:** Evita cascata de timeouts. Quando aberto, serve cache expirado
  (modo offline) ou retorna lista vazia sem espera.

### ADR-004: structlog para logging estruturado
- **Status:** Aceito (Sprint 4)
- **Contexto:** `logging` padrão do Python gera logs não-estruturados,
  difíceis de parsear por ferramentas como Loki ou Elasticsearch.
- **Decisão:** Usar structlog com JSON em produção e output colorido em dev.
- **Motivo:** Campos tipados (timestamp ISO, level, module) facilitam
  observabilidade. Zero overhead adicional significativo.

### ADR-005: Métricas Prometheus nativas
- **Status:** Aceito (Sprint 4)
- **Contexto:** Precisávamos de métricas operacionais sem dependência de APM comercial.
- **Decisão:** Usar `prometheus-client` com servidor HTTP dedicado na porta 8502.
  9 métricas cobrindo API, LLM, RAG e chat.
- **Motivo:** Padrão de mercado para K8s. Dashboard Grafana importável.
  Scraping por Prometheus requer zero configuração no app.

### ADR-006: Anthropic SDK direto (migração de Databricks)
- **Status:** Aceito (Sprint 2)
- **Contexto:** Databricks Serving Endpoint para Claude apresentou problemas
  de autenticação e latência adicional.
- **Decisão:** Usar Anthropic SDK diretamente com API key.
  `base_url` configurável mantida para eventual proxy futuro.
- **Motivo:** Simplicidade, menor latência, autenticação confiável.

---

## Segurança

- **Secrets**: Apenas via variáveis de ambiente (`pydantic-settings`), nunca em código
- **Docker**: Usuário não-root (`meteorag`), imagem slim, multi-stage
- **K8s**: Secrets K8s (não plain text), resource limits, HPA
- **Audit**: `bandit` + `pip-audit` no CI

---

## Deploy

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Developer│───▸│  GitHub  │───▸│  CI/CD   │───▸│  K8s     │
│  (push)  │    │  Actions │    │ (build + │    │  Cluster │
└──────────┘    └──────────┘    │  test +  │    └──────────┘
                                │  deploy) │
                                └──────────┘
```

- **CI**: lint (ruff + black + mypy) → test (pytest --cov) → build (Docker)
- **CD**: push image → Helm upgrade → rollout restart
- **HPA**: min 1, max 3 réplicas (CPU target 70%)
