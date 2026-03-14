# MeteoRAG — Arquitetura

> Documento de decisões arquiteturais — será expandido na Sprint 5.

## Diagrama de Fluxo (Alto Nível)

```
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌───────────┐
│  Usuário │────▸│ Streamlit │────▸│ RAG      │────▸│ LLM       │
│  (Chat)  │◂────│ UI        │◂────│ Pipeline │◂────│ (Claude)  │
└──────────┘     └─────┬─────┘     └────┬─────┘     └───────────┘
                       │                │
                       │           ┌────▼─────┐
                       │           │  INMET   │
                       │           │  Client  │
                       │           └────┬─────┘
                       │                │
                       │           ┌────▼─────┐
                       │           │  API     │
                       └───────────│  INMET   │
                                   └──────────┘
```

## Decisões Técnicas (ADRs)

### ADR-001: TF-IDF ao invés de embeddings semânticos
- **Status:** Aceito
- **Motivo:** Menor dependência, menor custo computacional, suficiente para domínio restrito (meteorologia MG)
- **Trade-off:** Menor recall semântico, compensado por chunking contextual rico
