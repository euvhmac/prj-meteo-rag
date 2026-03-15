# MeteoRAG — Sprint Planning

**Projeto:** MeteoRAG — Assistente Meteorológico com RAG  
**Metodologia:** Scrum adaptado (sprints de 1 semana)  
**Critério de prioridade:** MoSCoW (Must / Should / Could / Won't)  
**Equipe:** 1 desenvolvedor (Victor) + agente IA (Copilot/Claude)  
**Total de Sprints:** 6 (MVP em S1–S3, production-ready em S4–S5, Next.js UI em S6)

---

## Definition of Done (DoD) Global

Todo item é considerado "Done" somente quando:
- [ ] Código implementado e rodando localmente sem erros
- [ ] Testes unitários escritos (cobertura mínima conforme `copilot-instructions.md`)
- [ ] Sem erros de linting (ruff) e type checking (mypy)
- [ ] PR criado, revisado e mergeado em `develop`
- [ ] `README.md` ou doc relevante atualizada se necessário
- [ ] Nenhuma credencial exposta no código ou histórico de commits

---

## Sprint 0 — Fundação do Projeto
**Duração:** 1–2 dias | **Objetivo:** Repositório e infra base prontos para desenvolvimento

### Épico: Project Setup

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S0-01 | Criar repositório GitHub com estrutura de diretórios canônica | chore | Must | Estrutura conforme `copilot-instructions.md` seção 3 presente |
| S0-02 | Configurar `.gitignore`, `.dockerignore`, `.env.example` | chore | Must | Nenhum arquivo sensível rastreável |
| S0-03 | Criar `pyproject.toml` com black, ruff, mypy e pytest configurados | chore | Must | `ruff check .` e `black --check .` passam em projeto vazio |
| S0-04 | Criar `requirements.txt` e `requirements-dev.txt` com pins de versão | chore | Must | `pip install -r requirements.txt` em Python 3.11 sem erro |
| S0-05 | Adicionar copilot-instructions.md em `.github/` | docs | Must | Arquivo presente e commitado |
| S0-06 | Criar ISSUE_TEMPLATE para bug, feature e data_quality | chore | Should | 3 templates presentes em `.github/ISSUE_TEMPLATE/` |
| S0-07 | Criar PULL_REQUEST_TEMPLATE.md | chore | Should | Template presente, checklist alinhado ao DoD global |
| S0-08 | Configurar branch protection em `main` (requer PR + CI) | chore | Must | Branch protegida via GitHub Settings |
| S0-09 | Criar `config.py` com pydantic-settings e todas as vars mapeadas | feat | Must | `from meteorag.config import settings` funciona com `.env` |
| S0-10 | Adicionar `conftest.py` base com fixtures de dados mock INMET | test | Must | `pytest tests/` roda sem importar API real |

**Critério de aceite da Sprint:**  
Desenvolvedor consegue clonar o repo, criar o `.env` a partir do `.env.example`, instalar deps e rodar `pytest tests/` sem erro.

---

## Sprint 1 — Core: Dados + RAG Engine
**Duração:** 5 dias | **Objetivo:** Pipeline de dados INMET → RAG funcional e testado

### Épico: INMET Data Layer

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S1-01 | Implementar `inmet_client.py` — listar todas as estações automáticas | feat | Must | Endpoint `/estacoes/T` retorna lista com código e nome |
| S1-02 | Implementar fetch de dados horários por estação e intervalo de datas | feat | Must | Endpoint `/estacao/{start}/{end}/{id}` retorna lista de obs |
| S1-03 | Implementar fetch de alertas por estado | feat | Must | Endpoint `/alertas/{estado}/1` retorna lista (ou [] se 204) |
| S1-04 | Implementar `parse_observation()` — normalizar campos INMET para dict limpo | feat | Must | Valores 9999/-9999/null retornam `None`; tipo correto para todos os campos |
| S1-05 | Implementar `get_daily_summary()` — agregação diária de chuva e temperatura | feat | Must | Agregação correta: soma precipitação, max/min temp, contagem de obs |
| S1-06 | Implementar retry com backoff exponencial (max 3 tentativas) | feat | Must | Mock de falha temporária → 2ª ou 3ª tentativa bem-sucedida |
| S1-07 | Implementar cache em memória com TTL de 30 minutos | feat | Must | Segunda chamada com mesmos parâmetros não faz requisição HTTP |
| S1-08 | Mapear estações MG prioritárias (JF, Ubá/Muriaé, Barbacena, BH, Viçosa) | chore | Must | `ESTACOES` dict com código e cidade corretos |
| S1-09 | Testes unitários para `inmet_client.py` com fixtures (sem HTTP real) | test | Must | Cobertura ≥ 85%; todos os edge cases de parsing cobertos |
| S1-10 | Logging estruturado em todas as funções do client | chore | Must | `logger.info/warning/error` em todos os fluxos; zero `print()` |

### Épico: RAG Engine

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S1-11 | Implementar `chunker.py` — `build_daily_chunk()` com classificação de intensidade | feat | Must | Chunk inclui nível (sem chuva / fraca / moderada / forte / extrema) |
| S1-12 | Implementar `chunker.py` — `build_hourly_chunk()` para obs com precipitação > 0 | feat | Must | Apenas obs com chuva > 0 geram chunks horários |
| S1-13 | Implementar `chunker.py` — `build_alert_chunk()` para alertas INMET | feat | Must | Chunk inclui severidade, evento, vigência e municípios |
| S1-14 | Implementar `chunker.py` — `build_context_chunk()` visão macro semanal | feat | Must | Chunk inclui total de chuva, dias com chuva, dia mais chuvoso |
| S1-15 | Implementar `retriever.py` — classe `TFIDFRetriever` com indexação e busca | feat | Must | `retrieve("chuva forte JF", top_k=5)` retorna chunks relevantes |
| S1-16 | Implementar `retriever.py` — tokenização com suporte a caracteres PT-BR | feat | Must | Acentos e cedilha indexados e buscados corretamente |
| S1-17 | Implementar `pipeline.py` — classe `MeteoRAG` orquestrando client + chunker + retriever | feat | Must | `rag.index_city(...)` e `rag.build_rag_context(query)` funcionam |
| S1-18 | Testes unitários para `chunker.py` — todos os tipos de chunk | test | Must | Cobertura ≥ 90%; chunks com dados parciais/nulos cobertos |
| S1-19 | Testes unitários para `retriever.py` — retrieval e scoring | test | Must | Cobertura ≥ 90%; query sem resultado retorna [] |
| S1-20 | Teste de integração básico do pipeline (fixtures locais) | test | Should | `pipeline.py` indexa mock data e retorna contexto não vazio para query |

**Critério de aceite da Sprint:**  
`python -c "from meteorag.rag.pipeline import MeteoRAG; rag = MeteoRAG(); print('ok')"` funciona. Pytest com cobertura ≥ 80%.

---

## Sprint 2 — LLM + Interface Streamlit
**Duração:** 5 dias | **Objetivo:** App funcional end-to-end localmente

### Épico: LLM Integration

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S2-01 | Implementar `llm/client.py` — `get_client()` com suporte a API direta e Databricks | feat | Must | Funciona com `METEORAG_ANTHROPIC_BASE_URL` definida e não definida |
| S2-02 | Implementar `ask_stream()` — streaming de resposta com generator | feat | Must | Chunks de texto fluem corretamente via `yield` |
| S2-03 | Implementar `ask()` — versão não-streaming para testes e fallback | feat | Must | Retorna string completa; timeout de 30s tratado |
| S2-04 | System prompt final — persona MeteoRAG, instruções de interpretação meteorológica | feat | Must | Prompt inclui: persona, regras de interpretação numérica, citação INMET |
| S2-05 | Limitar histórico de chat a últimas 10 mensagens | feat | Must | Histórico > 10 mensagens truncado corretamente |
| S2-06 | Fallback de erro do LLM — mensagem amigável sem crash | feat | Must | Exceção do SDK capturada; usuário recebe mensagem explicativa |
| S2-07 | Testes unitários para `llm/client.py` com mock do Anthropic SDK | test | Must | Cobertura ≥ 70%; streaming e non-streaming testados |

### Épico: Streamlit UI

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S2-08 | Implementar layout base — sidebar + 3 tabs (Chat / Dados / Debug RAG) | feat | Must | Navegação funcional; sem erros de estado |
| S2-09 | Sidebar: configuração de API Key, Base URL e seleção de cidades | feat | Must | Vars de ambiente atualizadas corretamente ao salvar |
| S2-10 | Sidebar: botão "Carregar / Atualizar Dados" com barra de progresso | feat | Must | Progresso correto para N cidades selecionadas |
| S2-11 | Tab Chat: render de histórico com estilos distintos user/assistant | feat | Must | Balões visuais distintos; scroll para última mensagem |
| S2-12 | Tab Chat: input `st.chat_input` + streaming da resposta | feat | Must | Resposta aparece progressivamente; cursor ▌ durante streaming |
| S2-13 | Tab Chat: botões de perguntas sugeridas (quick actions) | feat | Should | Click em sugestão popula o input corretamente |
| S2-14 | Tab Chat: botão "Limpar conversa" | feat | Should | Histórico limpo; próxima mensagem começa sem contexto anterior |
| S2-15 | Tab Dados: métricas por cidade (chuva total, maior dia, temp média) | feat | Must | Métricas corretas baseadas nos summaries do RAG |
| S2-16 | Tab Dados: gráfico de barras comparativo de precipitação diária (Plotly) | feat | Must | Linhas de referência 30mm e 60mm; agrupado por cidade |
| S2-17 | Tab Dados: gráfico de linha de temperatura máxima diária (Plotly) | feat | Should | Cores distintas por cidade; marcadores em cada ponto |
| S2-18 | Tab Dados: tabela detalhada com selector de cidade | feat | Should | Colunas renomeadas em PT-BR; ocultação do índice |
| S2-19 | Tab Debug RAG: buscador de chunks com score visível | feat | Should | `retrieve(query, top_k=10)` exibe chunks + score + metadata |
| S2-20 | Alertas INMET no topo da página com card colorido por severidade | feat | Must | Vermelho para extremo/laranja; amarelo para demais |
| S2-21 | Tela de estado vazio (sem dados carregados) com instruções e tabela de estações | feat | Must | Usuário sabe o que fazer antes de carregar dados |
| S2-22 | Cache `@st.cache_data(ttl=1800)` em todas as funções de fetch | feat | Must | Segunda carga da mesma cidade não faz HTTP request |

**Critério de aceite da Sprint:**  
`streamlit run src/meteorag/ui/app.py` abre no browser. É possível carregar dados de JF e fazer uma pergunta recebendo resposta com streaming.

> **Nota de execução (Sprint 2):**  
> - API INMET ficou indisponível (HTTP 204 em todos os endpoints de dados, 404 em alertas).  
> - Migração realizada: **Open-Meteo** como fonte principal de dados, INMET apenas para alertas (best-effort).  
> - LLM migrado de Databricks proxy para **API direta Anthropic** (`claude-haiku-4-5-20251001`).  
> - Resultado: 193 testes, 93.09% cobertura, app funcional end-to-end.  
> - Commit: `2edd85e` em `develop`.

---

## Sprint 3 — Containerização + CI/CD
**Duração:** 5 dias | **Objetivo:** App rodando em container com pipeline CI/CD funcional

### Épico: Docker

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S3-01 | `Dockerfile` multi-stage (builder + runtime) com usuário não-root | chore | Must | `docker build` sem warnings; imagem < 300MB |
| S3-02 | Health check no Dockerfile via endpoint `/_stcore/health` | chore | Must | `docker inspect` mostra health check configurado |
| S3-03 | `docker-compose.yml` para desenvolvimento local com hot reload | chore | Must | `docker compose up` sobe app na porta 8501 |
| S3-04 | `docker-compose.prod.yml` sem volume mount, com env_file | chore | Must | Imagem usa ENV vars, não arquivo .env montado |
| S3-05 | `.dockerignore` excluindo tests/, docs/, *.md, __pycache__ | chore | Must | Build ignora arquivos desnecessários; verificar com `docker build` |
| S3-06 | Script `scripts/health_check.py` para validação pós-deploy | chore | Should | Script retorna exit 0 se app saudável, exit 1 caso contrário |

### Épico: GitHub Actions CI

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S3-07 | Workflow `ci.yml` — trigger em PR para `develop` e `main` | ci | Must | Workflow inicia automaticamente em todo PR |
| S3-08 | CI Step: checkout + setup Python 3.11 + install deps | ci | Must | Step passa em < 2 min |
| S3-09 | CI Step: `ruff check .` + `black --check .` | ci | Must | Falha se linting não passar |
| S3-10 | CI Step: `mypy src/meteorag/` | ci | Should | Falha se type errors encontrados |
| S3-11 | CI Step: `pytest tests/unit/ --cov=src/meteorag --cov-fail-under=80` | ci | Must | Falha se cobertura < 80% |
| S3-12 | CI Step: `docker build` para validar Dockerfile | ci | Must | Build deve completar sem erro |
| S3-13 | Workflow `cd.yml` — trigger em push para `main` | ci | Must | Deploy inicia apenas em merge para main |
| S3-14 | CD Step: build + tag + push imagem para GHCR com SHA e `latest` | ci | Must | Imagem disponível em `ghcr.io/<org>/meteorag:<sha>` |
| S3-15 | CD Step: deploy via `helm upgrade --install` no cluster K8s | ci | Must | Helm chart atualizado com nova imagem |
| S3-16 | Workflow `data-quality.yml` — cron diário verificando API INMET | ci | Should | Notifica via issue ou Slack se API retornar erro por >1h |

### Épico: Kubernetes Base

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S3-17 | `namespace.yaml` — namespace `meteorag` | chore | Must | `kubectl apply -f k8s/namespace.yaml` sem erro |
| S3-18 | `configmap.yaml` — vars não-sensíveis do app | chore | Must | ConfigMap com INMET_BASE_URL, LOG_LEVEL, etc |
| S3-19 | `secret.yaml` — template para ANTHROPIC_API_KEY (valor via CI) | chore | Must | Secret nunca contém valor real no repo |
| S3-20 | `deployment.yaml` — 1 réplica, resource limits, liveness/readiness probes | chore | Must | `kubectl rollout status` green |
| S3-21 | `service.yaml` — ClusterIP na porta 8501 | chore | Must | `kubectl get svc -n meteorag` mostra serviço |
| S3-22 | `hpa.yaml` — HPA min 1 / max 3 réplicas, CPU 70% | chore | Must | `kubectl get hpa -n meteorag` mostra configuração |

**Critério de aceite da Sprint:**  
Push para `main` aciona CI/CD end-to-end. Imagem publicada no registry. App rodando no K8s (pode ser cluster local via minikube/k3s para validação).

---

## Sprint 4 — Kubernetes Produção + Observabilidade
**Duração:** 5 dias | **Objetivo:** App production-ready com monitoramento

### Épico: Helm Charts

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S4-01 | `helm/meteorag/Chart.yaml` com versioning semântico | chore | Must | `helm lint helm/meteorag/` passa sem warnings |
| S4-02 | `helm/meteorag/values.yaml` com todos os defaults documentados | chore | Must | Cada valor tem comentário explicando seu propósito |
| S4-03 | `helm/meteorag/values.prod.yaml` — overrides para produção | chore | Must | Resource limits maiores; replicas mínimas = 2 |
| S4-04 | Templates Helm para deployment, service, ingress, configmap, HPA | chore | Must | `helm template meteorag helm/meteorag/ -f values.prod.yaml` válido |
| S4-05 | Ingress com TLS (cert-manager annotation) | chore | Should | Domínio acessível via HTTPS com certificado válido |

### Épico: Monitoramento

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S4-06 | Instrumentar app com `prometheus_client` — métricas de LLM e INMET | feat | Must | Endpoint `/metrics` exposto na porta 8502 |
| S4-07 | Métricas: counters para requests INMET (success/error) + latência | feat | Must | `meteorag_inmet_requests_total` visível no Prometheus |
| S4-08 | Métricas: counters para requests LLM + latência p95 | feat | Must | `meteorag_llm_requests_total` e `meteorag_llm_latency_seconds` |
| S4-09 | Métricas: gauge para total de chunks indexados | feat | Should | `meteorag_rag_chunks_total` atualizado após cada indexação |
| S4-10 | `monitoring/prometheus/rules.yaml` — alertas críticos | chore | Must | Alerta INMET offline > 5min; LLM latência > 10s |
| S4-11 | `monitoring/grafana/dashboard.json` — dashboard operacional | chore | Should | Dashboard com: uptime, latência LLM, chuva por cidade (últimas 24h) |
| S4-12 | Logging estruturado com `structlog` ou `logging` + JSON formatter | feat | Must | Logs em JSON com campos: timestamp, level, module, message |

### Épico: Resiliência

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S4-13 | Circuit breaker para API INMET — desabilitar temporariamente após N falhas | feat | Should | Após 5 falhas consecutivas, client entra em cooldown de 5min |
| S4-14 | Modo offline — servir dados do cache mesmo sem API INMET | feat | Should | Se INMET offline, app continua com dados em cache (badge "usando cache") |
| S4-15 | Rolling update strategy no Deployment K8s | chore | Must | Zero downtime em deploy; `maxUnavailable: 0` configurado |
| S4-16 | PodDisruptionBudget — min 1 pod disponível durante manutenção | chore | Should | `kubectl get pdb -n meteorag` mostra PDB configurado |

**Critério de aceite da Sprint:**  
App rodando em K8s com HTTPS. Métricas visíveis no Grafana. Rolling update sem downtime.

---

## Sprint 5 — Qualidade, Documentação e Launch
**Duração:** 5 dias | **Objetivo:** Projeto production-ready e público

### Épico: Qualidade e Testes Finais

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S5-01 | Testes de integração completos do pipeline RAG → LLM | test | Must | Teste end-to-end com dados reais INMET (marcado como integration) |
| S5-02 | Teste de carga básico com Locust — 50 usuários simultâneos | test | Should | App responde < 5s para 90% das requests sob carga |
| S5-03 | Revisão de cobertura global — atingir ≥ 80% | test | Must | `pytest --cov` reporta ≥ 80% global |
| S5-04 | Auditoria de segurança — scan com `bandit` + `pip-audit` | chore | Must | Sem issues de severidade HIGH ou CRITICAL |
| S5-05 | Review de todos os edge cases da API INMET (204, 503, timeout, dados parciais) | test | Must | Cada caso tem teste unitário correspondente |

### Épico: Documentação Final

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S5-06 | `README.md` completo com: badges CI, demo GIF, setup, estrutura, contribuição | docs | Must | README legível em < 5 min por novo desenvolvedor |
| S5-07 | `docs/ARCHITECTURE.md` — diagrama de arquitetura + decisões técnicas (ADRs) | docs | Must | Diagrama ASCII ou Mermaid do fluxo completo |
| S5-08 | `docs/API_REFERENCE.md` — referência completa das APIs externas | docs | Must | Arquivo já existente atualizado com exemplos reais |
| S5-09 | `docs/SPRINTS.md` — retrospectiva de cada sprint com aprendizados | docs | Should | Anotações de o que funcionou e o que mudou em relação ao planejado |
| S5-10 | Docstrings completas em todas as classes e funções públicas | docs | Must | `pydoc` gera documentação sem erros |
| S5-11 | CHANGELOG.md seguindo Keep a Changelog | docs | Should | Versão 1.0.0 documentada com todas as features |

### Épico: Experiência do Usuário

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S5-12 | Página "Sobre" — contexto do projeto, fontes de dados, limitações | feat | Should | Tab ou modal com informações sobre o projeto |
| S5-13 | Disclaimer visível sobre dados brutos INMET sem validação de consistência | feat | Must | Aviso conforme política oficial do INMET |
| S5-14 | Internacionalização básica — suporte a perguntas em EN além do PT-BR | feat | Could | System prompt detecta idioma e responde no mesmo idioma |
| S5-15 | Exportação de dados — CSV download dos summaries da sessão | feat | Could | Botão "Exportar CSV" na tab Dados |

**Critério de aceite da Sprint:**  
Projeto público no GitHub com README completo, CI verde, app rodando em produção, documentação completa.

> **Ao final da Sprint 5:**  
> - Merge `develop` → `main`, criar tag `v1.0.0`  
> - Criar branch `release/streamlit` a partir de `v1.0.0` (versão preservada)  
> - Deploy do backend Python (Streamlit + RAG) em Railway / Render / K8s

---

## Sprint 6 — Next.js Frontend + FastAPI Backend
**Duração:** 5 dias | **Objetivo:** UI moderna de chatbot com deploy na Vercel  
**Branch:** `feature/nextjs-frontend` (a partir de `develop`)

### Épico: FastAPI Backend (API REST)

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S6-01 | Criar `src/meteorag/api/server.py` — FastAPI app com CORS configurado | feat | Must | `uvicorn meteorag.api.server:app` sobe na porta 8000 |
| S6-02 | `POST /api/chat` — recebe query + history, retorna resposta via SSE streaming | feat | Must | Streaming funciona com `EventSource` no browser |
| S6-03 | `GET /api/weather/{city}` — retorna dados meteorológicos (daily + current) | feat | Must | JSON com sumários diários + condição atual da cidade |
| S6-04 | `GET /api/alerts` — retorna alertas INMET ativos (best-effort) | feat | Must | Lista de alertas ou `[]` se INMET indisponível |
| S6-05 | `GET /api/cities` — retorna lista de cidades monitoradas com coordenadas | feat | Should | JSON com `MG_CITIES` completo |
| S6-06 | `GET /api/health` — health check para Vercel/K8s | feat | Must | Retorna `{"status": "ok"}` com status 200 |
| S6-07 | Startup event — indexa cidades prioritárias ao iniciar servidor | feat | Must | RAG pipeline pronto para queries ao subir |
| S6-08 | Testes unitários para FastAPI com `httpx` + `TestClient` | test | Must | Cobertura ≥ 80% dos endpoints |

### Épico: Next.js Frontend (Chat UI)

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S6-09 | Inicializar `frontend/` com Next.js 14+ App Router + TypeScript + Tailwind | chore | Must | `npm run dev` sobe na porta 3000 |
| S6-10 | Layout base — header com logo MeteoRAG + nav + footer | feat | Must | Layout responsivo mobile-first |
| S6-11 | Página principal — chat interface com input, mensagens, streaming | feat | Must | Mensagens aparecem progressivamente via SSE |
| S6-12 | Componente `ChatMessage` — balões distintos user/assistant com markdown | feat | Must | Suporte a **bold**, listas, código inline |
| S6-13 | Componente `WeatherCard` — card com condição atual de cada cidade | feat | Should | Ícone WMO, temperatura, chuva, umidade |
| S6-14 | Componente `AlertBanner` — banner de alertas INMET no topo | feat | Must | Cores por severidade; dismissable |
| S6-15 | Perguntas sugeridas — chips clicáveis abaixo do input | feat | Should | Click popula e envia a pergunta |
| S6-16 | Dark mode toggle | feat | Could | Persiste preferência em localStorage |
| S6-17 | Botão "Modo Avançado (Streamlit)" — link externo para o Streamlit | feat | Must | Abre Streamlit em nova aba |
| S6-18 | Página "Sobre" — fontes de dados, limitações, créditos | feat | Should | Rota `/about` com informações do projeto |
| S6-19 | SEO — meta tags, Open Graph, favicon | chore | Should | Preview correto ao compartilhar link |
| S6-20 | Deploy na Vercel com env vars configuradas | chore | Must | `https://meteorag.vercel.app` funcional |

### Épico: Integração & Infra

| ID | Item | Tipo | Prioridade | DoD Específico |
|----|------|------|-----------|----------------|
| S6-21 | Atualizar Dockerfile para expor FastAPI (porta 8000) + Streamlit (porta 8501) | chore | Must | `docker compose up` sobe ambos os serviços |
| S6-22 | Atualizar Helm chart — novo Service para FastAPI | chore | Must | `helm template` inclui service na porta 8000 |
| S6-23 | CORS configurado para domínio Vercel + localhost dev | chore | Must | Frontend Vercel consegue chamar backend sem erro CORS |
| S6-24 | Atualizar CI — lint + test do frontend (ESLint + Jest/Vitest) | ci | Should | CI roda `npm run lint` e `npm test` no frontend |

**Critério de aceite da Sprint:**  
Chat funcional em `https://meteorag.vercel.app` conectando ao backend Python. Botão de switch para Streamlit funcionando. Deploy automatizado.

> **Ao final da Sprint 6:**  
> - Merge `feature/nextjs-frontend` → `develop` → `main`, criar tag `v2.0.0`  
> - Deploy: Vercel (Next.js) + Railway/K8s (Python backend com FastAPI + Streamlit)

---

## Backlog (Pós-MVP / Versão 2.0+)

| ID | Item | Prioridade | Observação |
|----|------|-----------|------------|
| BKL-01 | Embeddings semânticos (sentence-transformers) substituindo TF-IDF | Could | Melhora recall mas adiciona dependência pesada |
| BKL-02 | Suporte a múltiplos estados brasileiros além de MG | Could | Parametrizar estado na config |
| BKL-03 | Integração com ANA (Agência Nacional de Águas) para dados de rios e cheias | Could | API: `https://telemetriaws1.ana.gov.br` |
| BKL-04 | Agente com tool use — LLM decide quando chamar API INMET diretamente | Could | Requer refactor do pipeline |
| BKL-05 | Notificações automáticas via Telegram quando chuva > 50mm | Could | Bot Telegram + Webhook |
| BKL-06 | Histórico persistente de conversas (PostgreSQL) | Could | Requer PVC no K8s |
| BKL-07 | Fine-tuning de prompt para terminologia específica Defesa Civil | Won't | Fora do escopo MVP |
| BKL-08 | Suporte a dados GOES-16 (imagens de satélite) | Won't | Complexidade alta, escopo diferente |
| BKL-09 | PWA — instalar MeteoRAG como app no celular | Could | Service worker + manifest.json no Next.js |
| BKL-10 | WebSocket para atualizações em tempo real | Could | Push de alertas sem polling |
| BKL-11 | i18n no frontend Next.js (PT-BR / EN) | Could | `next-intl` ou similar |

---

## Mapa Visual das Sprints

```
Sprint 0 (1-2d)    Sprint 1 (5d)         Sprint 2 (5d)
├─ Setup Repo      ├─ INMET Client        ├─ LLM Client
├─ Config/Env      ├─ RAG Chunker         ├─ Streamlit UI
├─ CI base         ├─ TF-IDF Retriever    ├─ Chat streaming
└─ Templates       ├─ Open-Meteo Client   └─ Gráficos Plotly
                   └─ Unit Tests           
                                           
Sprint 3 (5d)          Sprint 4 (5d)         Sprint 5 (5d)
├─ Dockerfile          ├─ Helm Charts        ├─ Testes finais
├─ docker-compose      ├─ Prometheus         ├─ Documentação
├─ GitHub Actions CI   ├─ Grafana Dashboard  ├─ Launch público
├─ K8s base            ├─ Circuit breaker    └─ README final
└─ CD pipeline         └─ Rolling update        │
                                                 └─→ tag v1.0.0
                                                     branch release/streamlit

Sprint 6 (5d)
├─ FastAPI endpoints
├─ Next.js App Router
├─ Chat UI (Tailwind)
├─ Vercel deploy
├─ Switch Streamlit
└─→ tag v2.0.0
```

---

## Estratégia de Branches

```
develop ─── S3 ─── S4 ─── S5 ──┬── merge → main → tag v1.0.0
                                │       │
                                │       └─→ release/streamlit (preservada)
                                │
                                └── feature/nextjs-frontend (S6)
                                        │
                                        └── merge → main → tag v2.0.0
```

| Tag | Conteúdo | Deploy |
|-----|----------|--------|
| `v1.0.0` | Backend Python + Streamlit UI | K8s / Railway |
| `v2.0.0` | Backend Python + FastAPI + Next.js | K8s (backend) + Vercel (frontend) |
| `release/streamlit` | Versão Streamlit-only preservada | Pode rodar standalone |

---

## Métricas de Sucesso do Projeto

| Métrica | Meta |
|---------|------|
| Cobertura de testes | ≥ 80% global |
| Tempo de resposta LLM (p95) | < 8 segundos |
| Uptime em produção | ≥ 99% |
| Latência de indexação INMET (7 dias, 2 cidades) | < 30 segundos |
| Issues abertas sem assignee | 0 |
| Linhas de código sem type hints | 0 em módulos `src/` |
