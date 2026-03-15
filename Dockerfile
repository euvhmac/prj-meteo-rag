# ══════════════════════════════════════════════════════════
# MeteoRAG — Dockerfile (Multi-stage)
# Imagem final < 300MB, usuário não-root, health check
# ══════════════════════════════════════════════════════════

# ── Stage 1: Builder ─────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Instalar deps primeiro (cache de camada)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copiar código fonte
COPY src/ src/
COPY pyproject.toml .

# ── Stage 2: Runtime ─────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/victorliquiddata/meteorag" \
      org.opencontainers.image.description="MeteoRAG — Assistente Meteorológico com RAG" \
      org.opencontainers.image.licenses="MIT"

# Instalar curl para health check e limpar cache apt
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN groupadd -r meteorag && \
    useradd -r -g meteorag -d /app -s /sbin/nologin meteorag

WORKDIR /app

# Copiar deps instaladas do builder
COPY --from=builder /install /usr/local

# Copiar código fonte
COPY --from=builder /build/src ./src
COPY --from=builder /build/pyproject.toml .

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    METEORAG_APP_PORT=8501 \
    METEORAG_LOG_LEVEL=INFO \
    METEORAG_ENVIRONMENT=production

# Expor porta do Streamlit
EXPOSE 8501

# Health check via endpoint Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Trocar para usuário não-root
USER meteorag

# Entrypoint — Streamlit em modo headless
CMD ["python", "-m", "streamlit", "run", "src/meteorag/ui/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
