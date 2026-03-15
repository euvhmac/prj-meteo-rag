"""MeteoRAG — Streamlit entry point.

Interface principal do assistente meteorológico inteligente.
Layout: sidebar (config) + 3 tabs (Chat, Dados, Debug RAG).
"""

from __future__ import annotations

import logging
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from meteorag.api.openmeteo_client import MG_CITIES, OpenMeteoClient
from meteorag.config import Settings
from meteorag.llm.client import (
    FALLBACK_MESSAGE,
    ask_stream,
    get_client,
    trim_history,
)
from meteorag.logging import setup_logging
from meteorag.metrics import start_metrics_server
from meteorag.rag.pipeline import MeteoRAG

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Constantes
# ═══════════════════════════════════════════════════════════

SUGGESTED_QUESTIONS: list[str] = [
    "☔ Choveu em Juiz de Fora nos últimos dias?",
    "🌡️ Qual a temperatura máxima desta semana?",
    "⚠️ Há algum alerta meteorológico ativo?",
    "📊 Compare a chuva entre Juiz de Fora e Barbacena",
    "💧 Qual o dia mais chuvoso da semana?",
]

SEVERITY_COLORS: dict[str, str] = {
    "Grande Perigo": "#cc0000",
    "Perigo": "#ff6600",
    "Perigo Potencial": "#ffcc00",
    "Observação": "#3399ff",
}

PAGE_TITLE = "MeteoRAG — Assistente Meteorológico"
PAGE_ICON = "🌦️"

# ═══════════════════════════════════════════════════════════
# Funções com cache
# ═══════════════════════════════════════════════════════════


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_alerts(_settings: Settings) -> list[dict[str, Any]]:
    """Busca alertas INMET ativos para MG com cache de 30 min (best-effort)."""
    from meteorag.api.inmet_client import INMETClient

    try:
        client = INMETClient(_settings)
        return client.get_alerts("MG")
    except Exception:
        return []


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_daily_summaries(
    city: str,
    days_back: int,
) -> list[dict[str, Any]]:
    """Busca sumários diários via Open-Meteo com cache de 30 min."""
    client = OpenMeteoClient()
    return client.get_daily_summaries(city, days_back)


# ═══════════════════════════════════════════════════════════
# Session state init
# ═══════════════════════════════════════════════════════════


def init_session_state() -> None:
    """Inicializa variáveis do session_state com defaults."""
    defaults: dict[str, Any] = {
        "chat_history": [],
        "rag_pipeline": None,
        "data_loaded": False,
        "selected_cities": list(MG_CITIES.keys()),
        "llm_client": None,
        "settings": None,
        "alerts": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_settings() -> Settings:
    """Retorna Settings do session_state ou cria novo."""
    if st.session_state.settings is None:
        st.session_state.settings = Settings()
    result: Settings = st.session_state.settings
    return result


# ═══════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════


def render_sidebar() -> None:
    """Renderiza a sidebar com configurações e ações."""
    with st.sidebar:
        st.title("🌦️ MeteoRAG")
        st.caption("Assistente Meteorológico Inteligente")

        st.divider()

        # ── Configuração LLM ──
        with st.expander("⚙️ Configuração LLM", expanded=False):
            api_key = st.text_input(
                "API Key",
                value=get_settings().anthropic_api_key,
                type="password",
                help="Chave de acesso para o LLM (Anthropic/Databricks)",
            )
            base_url = st.text_input(
                "Base URL",
                value=get_settings().anthropic_base_url,
                help="URL do endpoint (deixe vazio para API direta Anthropic)",
            )
            model = st.text_input(
                "Modelo",
                value=get_settings().llm_model,
                help="Nome do modelo LLM",
            )

            if (
                api_key != get_settings().anthropic_api_key
                or base_url != get_settings().anthropic_base_url
            ):
                try:
                    new_settings = Settings(
                        anthropic_api_key=api_key,
                        anthropic_base_url=base_url,
                        llm_model=model,
                    )
                    st.session_state.settings = new_settings
                    st.session_state.llm_client = None
                except Exception:
                    pass

        st.divider()

        # ── Seleção de cidades ──
        st.subheader("📍 Cidades")
        all_cities = list(MG_CITIES.keys())
        selected = st.multiselect(
            "Selecione as cidades para monitorar",
            options=all_cities,
            default=st.session_state.selected_cities,
            help="Cidades da Zona da Mata e região de MG",
        )
        st.session_state.selected_cities = selected

        # ── Período ──
        days_back = st.slider(
            "Dias retroativos",
            min_value=1,
            max_value=30,
            value=get_settings().default_days_back,
            help="Quantidade de dias retroativos para buscar dados",
        )

        st.divider()

        # ── Botão de carregar dados ──
        load_clicked = st.button(
            "🔄 Carregar / Atualizar Dados",
            use_container_width=True,
            type="primary",
        )

        if load_clicked:
            _load_data(selected, days_back)

        # ── Status ──
        if st.session_state.data_loaded:
            rag: MeteoRAG = st.session_state.rag_pipeline
            st.success(f"✅ {rag.total_chunks} chunks indexados")
            st.caption(f"Cidades: {', '.join(rag.indexed_cities)}")
        else:
            st.info("Clique em **Carregar Dados** para começar")

        st.divider()

        # ── Info ──
        st.caption(
            "Dados: [Open-Meteo](https://open-meteo.com) + [INMET](https://portal.inmet.gov.br)"
        )
        st.caption("LLM: Claude Haiku (Anthropic)")
        st.caption("v0.4.0 — Sprint 4")


def _load_data(selected_cities: list[str], days_back: int) -> None:
    """Carrega dados do Open-Meteo e indexa no pipeline RAG."""
    if not selected_cities:
        st.sidebar.warning("Selecione ao menos uma cidade.")
        return

    settings = get_settings()
    rag = MeteoRAG(settings)

    progress = st.sidebar.progress(0, text="Iniciando...")
    total = len(selected_cities)

    for i, city in enumerate(selected_cities):
        progress.progress(
            (i + 1) / total,
            text=f"Carregando {city}... ({i + 1}/{total})",
        )
        rag.index_city(city, days_back)

    progress.progress(1.0, text="Concluído! ✅")

    st.session_state.rag_pipeline = rag
    st.session_state.data_loaded = True

    # Carrega alertas INMET (best-effort)
    st.session_state.alerts = fetch_alerts(settings)


# ═══════════════════════════════════════════════════════════
# Alertas no topo
# ═══════════════════════════════════════════════════════════


def render_alerts() -> None:
    """Renderiza alertas INMET ativos no topo da página."""
    alerts = st.session_state.get("alerts", [])
    if not alerts:
        return

    for alert in alerts[:5]:  # limita a 5 alertas
        severity = alert.get("severidade", alert.get("severity", ""))
        event = alert.get("evento", alert.get("event", ""))
        description = alert.get("descricao", alert.get("description", ""))
        cities_str = alert.get("municipios", alert.get("cities", ""))

        color = SEVERITY_COLORS.get(severity, "#888888")

        st.markdown(
            f"""<div style="
                background-color: {color}20;
                border-left: 4px solid {color};
                padding: 10px 15px;
                margin-bottom: 8px;
                border-radius: 4px;
            ">
                <strong>⚠️ {severity}: {event}</strong><br>
                <small>{description}</small><br>
                <small>Municípios: {cities_str[:200]}</small>
            </div>""",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════
# Tab Chat
# ═══════════════════════════════════════════════════════════


def render_tab_chat() -> None:
    """Renderiza a aba de chat com histórico e streaming."""
    # Botão limpar conversa
    _col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🗑️ Limpar", help="Limpar conversa"):
            st.session_state.chat_history = []
            st.rerun()

    # Verifica se dados estão carregados
    if not st.session_state.data_loaded:
        _render_empty_state()
        return

    # Renderiza histórico
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Perguntas sugeridas
    if not st.session_state.chat_history:
        st.markdown("### 💡 Perguntas sugeridas")
        cols = st.columns(len(SUGGESTED_QUESTIONS))
        for i, question in enumerate(SUGGESTED_QUESTIONS):
            with cols[i]:
                if st.button(question, key=f"suggest_{i}", use_container_width=True):
                    _handle_user_query(question)
                    st.rerun()

    # Input de chat
    if prompt := st.chat_input("Pergunte sobre o clima em MG..."):
        _handle_user_query(prompt)
        st.rerun()


def _handle_user_query(query: str) -> None:
    """Processa uma pergunta do usuário (streaming)."""
    # Adiciona mensagem do usuário
    st.session_state.chat_history.append({"role": "user", "content": query})

    settings = get_settings()
    rag: MeteoRAG = st.session_state.rag_pipeline

    # Busca contexto RAG
    context = rag.get_context_for_llm(query)

    # Prepara histórico trimado (sem a mensagem atual, que será enviada via build_messages)
    history = trim_history(st.session_state.chat_history[:-1])

    # Streaming do LLM
    try:
        if st.session_state.llm_client is None:
            st.session_state.llm_client = get_client(settings)

        full_response = ""
        for chunk in ask_stream(
            query=query,
            context=context,
            history=history,
            settings=settings,
            client=st.session_state.llm_client,
        ):
            full_response += chunk

        if not full_response:
            full_response = FALLBACK_MESSAGE

    except Exception as exc:
        logger.error("Erro no chat: %s", exc)
        full_response = FALLBACK_MESSAGE

    # Salva resposta no histórico
    st.session_state.chat_history.append({"role": "assistant", "content": full_response})


def _render_empty_state() -> None:
    """Renderiza tela de estado vazio com instruções."""
    st.markdown("---")
    st.markdown("""\n        ### 🌦️ Bem-vindo ao MeteoRAG!

        Para começar, **carregue os dados meteorológicos** usando o botão
        na barra lateral.

        #### O que o MeteoRAG pode fazer:
        - 📊 **Analisar dados climáticos** de cidades em MG (Open-Meteo + INMET)
        - 🌧️ **Responder perguntas** sobre chuva, temperatura e alertas
        - 📈 **Visualizar gráficos** de precipitação e temperatura
        - ⚠️ **Mostrar alertas** meteorológicos ativos (INMET)

        #### Cidades disponíveis:
        """)

    city_data = [
        {"Cidade": city, "Região": info["region"], "Altitude": f"{info['altitude']}m"}
        for city, info in MG_CITIES.items()
    ]
    st.table(city_data)

    st.info(
        "💡 **Dica:** Selecione as cidades na barra lateral e clique em "
        "'Carregar / Atualizar Dados' para começar!"
    )


# ═══════════════════════════════════════════════════════════
# Tab Dados
# ═══════════════════════════════════════════════════════════


def render_tab_dados() -> None:
    """Renderiza a aba de dados com métricas e gráficos."""
    if not st.session_state.data_loaded:
        st.info("Carregue os dados na barra lateral para visualizar métricas e gráficos.")
        return

    rag: MeteoRAG = st.session_state.rag_pipeline
    settings = get_settings()

    # Coleta sumários de todas as cidades indexadas
    all_summaries: dict[str, list[dict[str, Any]]] = {}
    for city in rag.indexed_cities:
        summaries = fetch_daily_summaries(city, settings.default_days_back)
        if summaries:
            all_summaries[city] = summaries

    if not all_summaries:
        st.warning("Nenhum dado disponível para as cidades selecionadas.")
        return

    # ── Métricas por cidade ──
    st.subheader("📊 Métricas por Cidade")
    cols = st.columns(min(len(all_summaries), 3))

    for i, (city, summaries) in enumerate(all_summaries.items()):
        with cols[i % len(cols)]:
            rain_values = [
                s["total_rain_mm"] for s in summaries if s.get("total_rain_mm") is not None
            ]
            temp_values = [s["max_temp_c"] for s in summaries if s.get("max_temp_c") is not None]

            total_rain = sum(rain_values) if rain_values else 0
            max_rain_day = max(rain_values) if rain_values else 0
            avg_temp = sum(temp_values) / len(temp_values) if temp_values else 0

            # Encontra dia mais chuvoso
            max_rain_date = ""
            for s in summaries:
                if s.get("total_rain_mm") == max_rain_day and max_rain_day > 0:
                    max_rain_date = s.get("date", "")[:10]
                    break

            st.markdown(f"#### {city}")
            st.metric("🌧️ Chuva total", f"{total_rain:.1f} mm")
            st.metric("💧 Dia mais chuvoso", f"{max_rain_day:.1f} mm", delta=max_rain_date)
            st.metric("🌡️ Temp. média máx.", f"{avg_temp:.1f} °C")

    st.divider()

    # ── Gráfico de precipitação ──
    st.subheader("🌧️ Precipitação Diária")
    _render_rain_chart(all_summaries)

    st.divider()

    # ── Gráfico de temperatura ──
    st.subheader("🌡️ Temperatura Máxima Diária")
    _render_temp_chart(all_summaries)

    st.divider()

    # ── Tabela detalhada ──
    st.subheader("📋 Dados Detalhados")
    _render_data_table(all_summaries)


def _render_rain_chart(all_summaries: dict[str, list[dict[str, Any]]]) -> None:
    """Gráfico de barras com precipitação diária (Plotly)."""
    fig = go.Figure()

    for city, summaries in all_summaries.items():
        dates = [s["date"] for s in summaries]
        rain = [s.get("total_rain_mm") or 0 for s in summaries]

        fig.add_trace(
            go.Bar(
                x=dates,
                y=rain,
                name=city,
                text=[f"{r:.1f} mm" for r in rain],
                textposition="auto",
            )
        )

    # Linhas de referência
    fig.add_hline(
        y=30,
        line_dash="dash",
        line_color="orange",
        annotation_text="Chuva forte (30mm)",
        annotation_position="top left",
    )
    fig.add_hline(
        y=60,
        line_dash="dash",
        line_color="red",
        annotation_text="Chuva muito forte (60mm)",
        annotation_position="top left",
    )

    fig.update_layout(
        barmode="group",
        xaxis_title="Data",
        yaxis_title="Precipitação (mm)",
        legend_title="Cidade",
        height=450,
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_temp_chart(all_summaries: dict[str, list[dict[str, Any]]]) -> None:
    """Gráfico de linhas com temperatura máxima diária (Plotly)."""
    fig = go.Figure()

    for city, summaries in all_summaries.items():
        dates = [s["date"] for s in summaries]
        temps = [s.get("max_temp_c") for s in summaries]

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=temps,
                mode="lines+markers",
                name=city,
                line={"width": 2},
            )
        )

    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Temperatura Máxima (°C)",
        legend_title="Cidade",
        height=400,
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_data_table(all_summaries: dict[str, list[dict[str, Any]]]) -> None:
    """Tabela detalhada de dados com filtro por cidade."""
    cities = list(all_summaries.keys())
    selected_city = st.selectbox("Selecione a cidade", options=cities)

    if selected_city and selected_city in all_summaries:
        summaries = all_summaries[selected_city]

        table_data = []
        for s in sorted(summaries, key=lambda x: x.get("date", ""), reverse=True):
            table_data.append(
                {
                    "Data": s.get("date", ""),
                    "Chuva (mm)": (
                        f"{s['total_rain_mm']:.1f}" if s.get("total_rain_mm") is not None else "—"
                    ),
                    "Temp. Máx (°C)": (
                        f"{s['max_temp_c']:.1f}" if s.get("max_temp_c") is not None else "—"
                    ),
                    "Temp. Mín (°C)": (
                        f"{s['min_temp_c']:.1f}" if s.get("min_temp_c") is not None else "—"
                    ),
                    "Umidade Média (%)": (
                        f"{s['avg_humidity_pct']:.1f}"
                        if s.get("avg_humidity_pct") is not None
                        else "—"
                    ),
                    "Observações": s.get("observation_count", 0),
                }
            )

        st.dataframe(table_data, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
# Tab Debug RAG
# ═══════════════════════════════════════════════════════════


def render_tab_debug() -> None:
    """Renderiza a aba de debug do RAG com busca de chunks."""
    if not st.session_state.data_loaded:
        st.info("Carregue os dados para testar o motor de busca RAG.")
        return

    rag: MeteoRAG = st.session_state.rag_pipeline

    st.markdown(
        f"**Índice:** {rag.total_chunks} chunks | " f"**Cidades:** {', '.join(rag.indexed_cities)}"
    )

    # Busca
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        debug_query = st.text_input(
            "🔍 Busca no índice RAG",
            placeholder="Ex: chuva forte juiz de fora",
        )
    with col2:
        top_k = st.number_input("Top K", min_value=1, max_value=50, value=8)
    with col3:
        filter_type = st.selectbox(
            "Tipo",
            options=["Todos", "daily", "hourly", "alert", "context"],
        )

    if debug_query:
        ft = None if filter_type == "Todos" else filter_type
        results = rag.retrieve(debug_query, top_k=top_k, filter_type=ft)

        if not results:
            st.warning("Nenhum resultado encontrado.")
        else:
            st.markdown(f"**{len(results)} resultados encontrados:**")
            for i, chunk in enumerate(results, 1):
                score = chunk.get("score", 0)
                text = chunk.get("text", "")
                meta = chunk.get("metadata", {})

                # Cor do score
                if score > 0.3:
                    score_color = "🟢"
                elif score > 0.1:
                    score_color = "🟡"
                else:
                    score_color = "🔴"

                with st.expander(
                    f"{score_color} #{i} — Score: {score:.4f} | "
                    f"{meta.get('type', '?')} | {meta.get('city', '?')} | "
                    f"{meta.get('date', '?')}",
                    expanded=i <= 3,
                ):
                    st.markdown(f"```\n{text}\n```")
                    st.json(meta)

    # Contexto completo para LLM
    st.divider()
    st.subheader("📝 Contexto para LLM")
    context_query = st.text_input(
        "Query para contexto",
        placeholder="Mesma query do chat — veja o contexto que será enviado ao LLM",
        key="context_query",
    )
    if context_query:
        context = rag.get_context_for_llm(context_query)
        st.text_area("Contexto gerado", value=context, height=300, disabled=True)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════


def main() -> None:
    """Entry point principal do Streamlit."""
    # Inicializa logging estruturado e servidor de métricas
    _settings = Settings()
    setup_logging(level=_settings.log_level, environment=_settings.environment)
    start_metrics_server(port=8502)

    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    # Sidebar
    render_sidebar()

    # Alertas no topo
    render_alerts()

    # Tabs principais
    tab_chat, tab_dados, tab_debug = st.tabs(["💬 Chat", "📊 Dados", "🔧 Debug RAG"])

    with tab_chat:
        render_tab_chat()

    with tab_dados:
        render_tab_dados()

    with tab_debug:
        render_tab_debug()


if __name__ == "__main__":
    main()
