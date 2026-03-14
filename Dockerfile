# ══════════════════════════════════════════════════════════
# MeteoRAG — Dockerfile (Multi-stage)
# ══════════════════════════════════════════════════════════

# ── Stage 1: Builder ─────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY src/ src/

# ── Stage 2: Runtime ─────────────────────────────────────
FROM python:3.11-slim AS runtime

# Criar usuário não-root
RUN groupadd -r meteorag && useradd -r -g meteorag -d /app -s /sbin/nologin meteorag

WORKDIR /app

# Copiar deps instaladas
COPY --from=builder /install /usr/local

# Copiar código fonte
COPY --from=builder /build/src ./src

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    METEORAG_APP_PORT=8501 \
    METEORAG_LOG_LEVEL=INFO \
    METEORAG_ENVIRONMENT=production

# Expor porta do Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Trocar para usuário não-root
USER meteorag

# Entrypoint
CMD ["python", "-m", "streamlit", "run", "src/meteorag/ui/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
