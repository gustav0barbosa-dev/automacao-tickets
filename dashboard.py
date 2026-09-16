# ============================================================
# dashboard.py - Dashboard de Análise (Protótipo)
# ============================================================
"""
Dashboard interativo dos tickets do Help360.

Uso:
    streamlit run dashboard.py
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==================== TEMA ====================
from pathlib import Path
_css = (Path(__file__).parent / 'estilo.css').read_text(encoding='utf-8')
st.markdown(f'<style>{_css}</style>', unsafe_allow_html=True)

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title='Automação Help360',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

RAIZ = Path(__file__).parent
CAMINHO_BANCO = RAIZ / 'dados' / 'tickets.db'


# ============================================================
# CARREGAMENTO DE DADOS
# ============================================================
@st.cache_data(ttl=300)
def carregar_tickets():
    """Carrega todos os tickets do banco."""
    if not CAMINHO_BANCO.exists():
        return None

    conn = sqlite3.connect(CAMINHO_BANCO)
    df = pd.read_sql('SELECT * FROM tickets', conn)
    conn.close()

    # Converte colunas de data
    colunas_data = ['criado_data', 'alterado_data', 'previsao',
                    'data_resolvido', 'data_1_resolvido']
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Colunas derivadas
    df['dias_aberto'] = (pd.Timestamp.now() - df['criado_data']).dt.days
    df['dias_resolucao'] = (df['data_resolvido'] - df['criado_data']).dt.days
    df['dias_1a_resposta'] = (df['data_1_resolvido'] - df['criado_data']).dt.days

    # Status SLA
    df['sla_status'] = 'em_andamento'
    mask_resolvido = df['data_resolvido'].notna()
    df.loc[mask_resolvido & (df['data_resolvido'] <= df['previsao']), 'sla_status'] = 'cumprido'
    df.loc[mask_resolvido & (df['data_resolvido'] > df['previsao']), 'sla_status'] = 'estourado'

    # Prioridade numérica para ordenação
    ordem_prioridade = {
        'Crítica': 1, 'Alta': 2, 'Média': 3,
        'Baixa-1': 4, 'Baixa-2': 5, 'Baixa-3': 6,
    }
    df['prioridade_ordem'] = df['prioridade'].map(ordem_prioridade).fillna(99)

    return df


@st.cache_data(ttl=300)
def carregar_snapshots():
    """Carrega histórico de snapshots."""
    if not CAMINHO_BANCO.exists():
        return None

    conn = sqlite3.connect(CAMINHO_BANCO)
    df = pd.read_sql('SELECT * FROM snapshots ORDER BY data_execucao DESC', conn)
    conn.close()

    if 'data_execucao' in df.columns:
        df['data_execucao'] = pd.to_datetime(df['data_execucao'], errors='coerce')

    return df


# ============================================================
# HELPERS DE UI
# ============================================================
def metrica(label, valor, delta=None, delta_color='normal', ajuda=None):
    """Renderiza um KPI com suporte a delta_color e help."""
    st.metric(
        label=label,
        value=valor,
        delta=delta,
        delta_color=delta_color,
        help=ajuda,
    )


def box_insight(texto):
    """Caixa de insight/destaque."""
    st.info(f'💡 **Insight:** {texto}')


def box_alerta(texto):
    """Caixa de alerta."""
    st.warning(f'⚠️ {texto}')


# ============================================================
# FILTROS
# ============================================================
def aplicar_filtros(df):
    """Aplica os filtros do sidebar e retorna o df filtrado."""
    st.sidebar.markdown('### 🔍 Filtros')

    # Período
    if df['criado_data'].notna().any():
        data_min = df['criado_data'].min().date()
        data_max = df['criado_data'].max().date()
    else:
        data_min = data_max = datetime.now().date()

    periodo = st.sidebar.date_input(
        'Período (criado em)',
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
    )

    if len(periodo) == 2:
        data_ini, data_fim = periodo
        df = df[
            (df['criado_data'].dt.date >= data_ini) &
            (df['criado_data'].dt.date <= data_fim)
        ]

    # Status
    status_unicos = sorted(df['status'].dropna().unique().tolist())
    status_sel = st.sidebar.multiselect(
        'Status',
        options=status_unicos,
        default=status_unicos,
    )
    if status_sel:
        df = df[df['status'].isin(status_sel)]

    # Categoria
    cat_unicas = sorted(df['categoria'].dropna().unique().tolist())
    cat_sel = st.sidebar.multiselect(
        'Categoria',
        options=cat_unicas,
        default=[],
        placeholder='Todas as categorias',
    )
    if cat_sel:
        df = df[df['categoria'].isin(cat_sel)]

    # Responsável
    resp_unicos = sorted(df['responsavel_atual'].dropna().unique().tolist())
    resp_unicos = [r for r in resp_unicos if r and r != 'Não informado']
    resp_sel = st.sidebar.multiselect(
        'Responsável',
        options=resp_unicos,
        default=[],
        placeholder='Todos os responsáveis',
    )
    if resp_sel:
        df = df[df['responsavel_atual'].isin(resp_sel)]

    # Mostra total
    st.sidebar.markdown(f'---')
    st.sidebar.metric('Tickets filtrados', len(df))

    return df


# ============================================================
# PÁGINA 1 — VISÃO GERAL
# ============================================================
def pagina_visao_geral(df, df_snap):
    st.title('Visão Geral')
    st.caption('Panorama geral dos tickets no período selecionado.')

    # ==================== CÁLCULOS ====================
    total = len(df)
    resolvidos = len(df[df['status'].isin(['Resolvido', 'Fechado'])])
    em_aberto = len(df[~df['status'].isin(['Resolvido', 'Fechado', 'Cancelado', 'Duplicado'])])

    # SLA
    df_sla = df[df['sla_status'].isin(['cumprido', 'estourado'])]
    cumpridos = len(df_sla[df_sla['sla_status'] == 'cumprido'])
    estourados = len(df_sla[df_sla['sla_status'] == 'estourado'])
    total_com_sla = cumpridos + estourados

    # % SLA sobre resolvidos (correto)
    perc_sla_resolvidos = (cumpridos / total_com_sla * 100) if total_com_sla > 0 else 0

    # % SLA sobre o total geral (visão mais conservadora)
    perc_sla_geral = (cumpridos / total * 100) if total > 0 else 0

    # Aging
    df_aberto = df[~df['status'].isin(['Resolvido', 'Fechado', 'Cancelado', 'Duplicado'])]
    aging = df_aberto['dias_aberto'].mean() if not df_aberto.empty else 0

    # ==================== KPIs ====================
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        metrica('Total de Tickets', f'{total}')

    with col2:
        metrica(
            'Resolvidos',
            f'{resolvidos}',
            delta=f'{resolvidos/total*100:.0f}%' if total else None,
        )

    with col3:
        metrica('Em Aberto', f'{em_aberto}')

    with col4:
        metrica(
            '% SLA (resolvidos)',
            f'{perc_sla_resolvidos:.0f}%',
            delta=f'{perc_sla_geral:.0f}% do total geral',
            ajuda=(
                f'{cumpridos} cumpridos, {estourados} estourados. '
                f'O delta mostra a fração de cumpridos sobre TODOS os {total} tickets.'
            ),
        )

    with col5:
        metrica(
            'Aging Médio (dias)',
            f'{aging:.1f}' if pd.notna(aging) else '—',
            delta='⚠️ Alto' if aging > 15 else '✅ OK',
            delta_color='inverse' if aging > 15 else 'normal',
            ajuda='Média de dias que tickets em aberto estão aguardando',
        )

    st.markdown('---')

    # ==================== GRÁFICOS ====================
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.subheader('📊 Distribuição por Status')
        status_count = df['status'].value_counts().reset_index()
        status_count.columns = ['Status', 'Quantidade']

        fig = px.pie(
            status_count,
            values='Quantidade',
            names='Status',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_dir:
        st.subheader('🎯 Prioridade')
        prio_count = df['prioridade'].value_counts().reset_index()
        prio_count.columns = ['Prioridade', 'Quantidade']

        fig = px.bar(
            prio_count,
            x='Quantidade',
            y='Prioridade',
            orientation='h',
            color='Prioridade',
            color_discrete_sequence=px.colors.qualitative.Safe,
            text='Quantidade',
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')

    # ==================== TOP CATEGORIAS ====================
    st.subheader('📁 Top 10 Categorias')
    cat_count = df['categoria'].value_counts().head(10).reset_index()
    cat_count.columns = ['Categoria', 'Quantidade']

    fig = px.bar(
        cat_count,
        x='Categoria',
        y='Quantidade',
        color='Quantidade',
        color_continuous_scale='Blues',
        text='Quantidade',
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(height=400, xaxis_tickangle=-30, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    # ==================== INSIGHTS ====================
    st.markdown('---')
    st.subheader('💡 Insights')

    # SLA
    if perc_sla_resolvidos < 70:
        box_alerta(f'SLA dos resolvidos está em **{perc_sla_resolvidos:.1f}%** — abaixo da meta (95%).')
    else:
        box_insight(f'SLA dos resolvidos está em **{perc_sla_resolvidos:.1f}%**.')

    # Aviso sobre SLA parcial
    if em_aberto > (total * 0.3):
        box_alerta(
            f'**{em_aberto} de {total} tickets** ({em_aberto/total*100:.0f}%) estão em aberto. '
            f'O SLA só pode ser avaliado após a resolução.'
        )

    # Aging
    if aging > 15:
        box_alerta(f'Aging médio em aberto é **{aging:.0f} dias** — tickets antigos acumulando.')

    # Tickets esquecidos
    esquecidos = len(df_aberto[df_aberto['dias_aberto'] > 30])
    if esquecidos > 0:
        box_alerta(
            f'**{esquecidos} tickets** estão em aberto há mais de 30 dias. '
            f'Priorize os mais antigos.'
        )

    # Snapshot
    if df_snap is not None and len(df_snap) > 0:
        ultima = df_snap.iloc[0]
        st.markdown(f'**Última carga:** {ultima["data_execucao"]:%d/%m/%Y %H:%M} '
                    f'({ultima["tickets_total"]} tickets no total)')


# ============================================================
# PÁGINA 2 — TEMPO DE RESPOSTA
# ============================================================
def pagina_tempo_resposta(df):
    st.title('⏱️ Tempo de Resposta')
    st.caption('Análise dos tempos de resolução e primeira resposta.')

    # Filtra só resolvidos
    df_res = df[df['dias_resolucao'].notna()].copy()

    if df_res.empty:
        st.warning('Sem tickets resolvidos no período.')
        return

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metrica('Tempo Médio', f'{df_res["dias_resolucao"].mean():.1f} dias')
    with col2:
        metrica('Mediana (P50)', f'{df_res["dias_resolucao"].median():.0f} dias')
    with col3:
        metrica('P90', f'{df_res["dias_resolucao"].quantile(0.9):.0f} dias')
    with col4:
        metrica('P99', f'{df_res["dias_resolucao"].quantile(0.99):.0f} dias')

    st.markdown('---')

    # Distribuição
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.subheader('📊 Distribuição de Tempo')
        fig = px.histogram(
            df_res, x='dias_resolucao', nbins=20,
            labels={'dias_resolucao': 'Dias para resolução'},
            color_discrete_sequence=['#3498db'],
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_dir:
        st.subheader('📋 Estatísticas')
        stats = pd.DataFrame({
            'Métrica': ['Mínimo', 'P25', 'Mediana', 'P75', 'P90', 'Máximo'],
            'Dias': [
                f'{df_res["dias_resolucao"].min():.0f}',
                f'{df_res["dias_resolucao"].quantile(0.25):.0f}',
                f'{df_res["dias_resolucao"].median():.0f}',
                f'{df_res["dias_resolucao"].quantile(0.75):.0f}',
                f'{df_res["dias_resolucao"].quantile(0.90):.0f}',
                f'{df_res["dias_resolucao"].max():.0f}',
            ]
        })
        st.dataframe(stats, hide_index=True, use_container_width=True)

    st.markdown('---')

    # Por categoria
    st.subheader('📁 Tempo Médio por Categoria')
    cat_tempo = df_res.groupby('categoria').agg(
        total=('id', 'count'),
        dias_medio=('dias_resolucao', 'mean'),
        dias_1a=('dias_1a_resposta', 'mean'),
    ).reset_index()
    cat_tempo = cat_tempo[cat_tempo['total'] >= 3].sort_values('dias_medio', ascending=True)

    fig = px.bar(
        cat_tempo,
        x='dias_medio',
        y='categoria',
        orientation='h',
        color='dias_medio',
        color_continuous_scale='RdYlGn_r',
        text=cat_tempo['dias_medio'].round(1),
        labels={'dias_medio': 'Dias (médio)', 'categoria': ''},
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(height=max(300, len(cat_tempo) * 35), coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    # Insight
    if not cat_tempo.empty:
        pior = cat_tempo.iloc[-1]
        melhor = cat_tempo.iloc[0]
        box_insight(
            f'**{pior["categoria"]}** é a categoria mais lenta '
            f'(**{pior["dias_medio"]:.1f} dias**). '
            f'Já **{melhor["categoria"]}** resolve em '
            f'**{melhor["dias_medio"]:.1f} dias**.'
        )

    st.markdown('---')

    # Por prioridade
    st.subheader('🎯 Tempo Médio por Prioridade')
    prio_tempo = df_res.groupby('prioridade').agg(
        total=('id', 'count'),
        dias_medio=('dias_resolucao', 'mean'),
    ).reset_index()
    prio_tempo['ordem'] = prio_tempo['prioridade'].map(
        {'Crítica': 1, 'Alta': 2, 'Média': 3, 'Baixa-1': 4, 'Baixa-2': 5, 'Baixa-3': 6}
    ).fillna(99)
    prio_tempo = prio_tempo.sort_values('ordem')

    fig = px.bar(
        prio_tempo,
        x='prioridade',
        y='dias_medio',
        color='dias_medio',
        color_continuous_scale='RdYlGn_r',
        text=prio_tempo['dias_medio'].round(1),
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(height=400, coloraxis_showscale=False, xaxis_title='')
    st.plotly_chart(fig, use_container_width=True)

    # Alerta de prioridade invertida
    critica = prio_tempo[prio_tempo['prioridade'] == 'Crítica']['dias_medio'].values
    alta = prio_tempo[prio_tempo['prioridade'] == 'Alta']['dias_medio'].values
    if len(critica) > 0 and len(alta) > 0 and critica[0] > alta[0]:
        box_alerta(
            f'Prioridade **Crítica** está demorando mais que **Alta** '
            f'({critica[0]:.1f} vs {alta[0]:.1f} dias). Verifique o processo de triagem.'
        )


# ============================================================
# PÁGINA 3 — SLA
# ============================================================
def pagina_sla(df):
    st.title('📊 SLA — Acordo de Nível de Serviço')
    st.caption('Cumprimento dos prazos acordados.')

    # Considera apenas tickets com SLA definido
    df_sla = df[df['previsao'].notna() & df['sla_status'].isin(['cumprido', 'estourado'])].copy()

    if df_sla.empty:
        st.warning('Sem tickets com SLA definido no período.')
        return

    cumpridos = len(df_sla[df_sla['sla_status'] == 'cumprido'])
    estourados = len(df_sla[df_sla['sla_status'] == 'estourado'])
    total = len(df_sla)
    perc = cumpridos / total * 100 if total > 0 else 0

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metrica('Total com SLA', f'{total}')
    with col2:
        metrica('% Cumprido', f'{perc:.1f}%',
                delta=f'{cumpridos} tickets')
    with col3:
        metrica('Estourados', f'{estourados}',
                delta=f'{estourados/total*100:.0f}%', delta_color='inverse')
    with col4:
        # Margem média
        df_sla['margem_dias'] = (df_sla['previsao'] - df_sla['data_resolvido']).dt.days
        margem_media = df_sla['margem_dias'].mean()
        metrica('Margem Média', f'{margem_media:+.1f} dias')

    st.markdown('---')

    # Pizza geral
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.subheader('📊 Status Geral')
        fig = px.pie(
            values=[cumpridos, estourados],
            names=['Cumprido', 'Estourado'],
            hole=0.4,
            color_discrete_map={'Cumprido': '#2ecc71', 'Estourado': '#e74c3c'},
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_dir:
        st.subheader('📊 Por Prioridade')
        prio_sla = df_sla.groupby('prioridade').agg(
            total=('id', 'count'),
            cumpridos=('sla_status', lambda x: (x == 'cumprido').sum()),
        ).reset_index()
        prio_sla['perc'] = prio_sla['cumpridos'] / prio_sla['total'] * 100
        prio_sla['ordem'] = prio_sla['prioridade'].map(
            {'Crítica': 1, 'Alta': 2, 'Média': 3, 'Baixa-1': 4, 'Baixa-2': 5, 'Baixa-3': 6}
        ).fillna(99)
        prio_sla = prio_sla.sort_values('ordem')

        fig = px.bar(
            prio_sla,
            x='prioridade',
            y='perc',
            color='perc',
            color_continuous_scale='RdYlGn',
            text=prio_sla['perc'].round(1),
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(height=350, coloraxis_showscale=False,
                          yaxis_title='% SLA cumprido', xaxis_title='')
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')

    # Por categoria
    st.subheader('📁 Ranking por Categoria')
    cat_sla = df_sla.groupby('categoria').agg(
        total=('id', 'count'),
        cumpridos=('sla_status', lambda x: (x == 'cumprido').sum()),
    ).reset_index()
    cat_sla = cat_sla[cat_sla['total'] >= 3].copy()
    cat_sla['perc'] = cat_sla['cumpridos'] / cat_sla['total'] * 100
    cat_sla = cat_sla.sort_values('perc')

    fig = px.bar(
        cat_sla,
        x='perc',
        y='categoria',
        orientation='h',
        color='perc',
        color_continuous_scale='RdYlGn',
        text=cat_sla['perc'].round(1),
        labels={'perc': '% SLA cumprido', 'categoria': ''},
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(height=max(300, len(cat_sla) * 35), coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    # Insights
    if not cat_sla.empty:
        pior = cat_sla.iloc[0]
        box_alerta(
            f'Categoria **{pior["categoria"]}** tem apenas '
            f'**{pior["perc"]:.1f}%** de SLA cumprido '
            f'({pior["cumpridos"]}/{pior["total"]} tickets).'
        )


# ============================================================
# PÁGINA 4 — PRODUTIVIDADE
# ============================================================
def pagina_produtividade(df):
    st.title('👥 Produtividade por Responsável')
    st.caption('Análise de volume e tempo por analista.')

    # Filtra responsáveis válidos
    df_resp = df[
        df['responsavel_atual'].notna() &
        (df['responsavel_atual'] != '') &
        (df['responsavel_atual'] != 'Não informado')
    ].copy()

    if df_resp.empty:
        st.warning('Sem responsáveis identificados.')
        return

    # Agrega por responsável
    agg = df_resp.groupby('responsavel_atual').agg(
        total=('id', 'count'),
        resolvidos=('status', lambda x: x.isin(['Resolvido', 'Fechado']).sum()),
        em_aberto=('status', lambda x: (~x.isin(['Resolvido', 'Fechado', 'Cancelado'])).sum()),
        dias_medio=('dias_resolucao', 'mean'),
    ).reset_index()
    agg.columns = ['Responsável', 'Total', 'Resolvidos', 'Em Aberto', 'Dias Médio']
    agg['% Resolução'] = (agg['Resolvidos'] / agg['Total'] * 100).round(1)
    agg['Dias Médio'] = agg['Dias Médio'].round(1)
    agg = agg.sort_values('Total', ascending=False)

    # KPIs
    col1, col2, col3 = st.columns(3)

    with col1:
        metrica('Analistas Ativos', f'{len(agg)}')
    with col2:
        metrica('Total de Tickets', f'{agg["Total"].sum()}')
    with col3:
        metrica('Média por Analista', f'{agg["Total"].mean():.0f} tickets')

    st.markdown('---')

    # Ranking por volume
    st.subheader('🏆 Ranking por Volume')

    fig = px.bar(
        agg.sort_values('Total', ascending=True),
        x='Total',
        y='Responsável',
        orientation='h',
        color='Dias Médio',
        color_continuous_scale='RdYlGn_r',
        text='Total',
        hover_data=['Resolvidos', 'Em Aberto', '% Resolução', 'Dias Médio'],
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(height=max(400, len(agg) * 35))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')

    # Dispersão volume × tempo
    st.subheader('🎯 Volume vs. Tempo Médio')

    fig = px.scatter(
        agg,
        x='Total',
        y='Dias Médio',
        size='Em Aberto',
        color='% Resolução',
        color_continuous_scale='RdYlGn',
        hover_name='Responsável',
        text='Responsável',
        labels={'Total': 'Tickets atribuídos', 'Dias Médio': 'Dias médio de resolução'},
    )
    fig.update_traces(textposition='top center', textfont_size=10)
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    box_insight(
        'Tamanho da bolha = tickets em aberto. '
        'Cor = % de resolução. '
        'Analistas com muitas atribuições e dias altos podem estar sobrecarregados.'
    )

    st.markdown('---')

    # Tabela detalhada
    st.subheader('📋 Tabela Detalhada')
    st.dataframe(
        agg,
        hide_index=True,
        use_container_width=True,
        column_config={
            '% Resolução': st.column_config.ProgressColumn(
                '% Resolução',
                help='% de tickets resolvidos/fechados',
                min_value=0,
                max_value=100,
                format='%.1f%%',
            ),
        }
    )

    # Alertas
    st.markdown('---')
    st.subheader('⚠️ Alertas de Sobrecarga')

    for _, row in agg.iterrows():
        if row['Em Aberto'] >= 10:
            box_alerta(f'**{row["Responsável"]}** tem **{row["Em Aberto"]} tickets em aberto**.')
        elif row['Dias Médio'] > 5 and pd.notna(row['Dias Médio']):
            box_alerta(f'**{row["Responsável"]}** tem tempo médio de **{row["Dias Médio"]:.1f} dias** — acima da média.')


# ============================================================
# PÁGINA 5 — BACKLOG
# ============================================================
def pagina_backlog(df):
    st.title('📋 Backlog Atual')
    st.caption('Tickets em aberto, aging e prioritários.')

    # Filtra em aberto
    status_fechados = ['Resolvido', 'Fechado', 'Cancelado', 'Duplicado']
    df_aberto = df[~df['status'].isin(status_fechados)].copy()

    if df_aberto.empty:
        st.success('🎉 Sem tickets em aberto!')
        return

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metrica('Total em Aberto', f'{len(df_aberto)}')
    with col2:
        aging = df_aberto['dias_aberto'].mean()
        metrica('Aging Médio', f'{aging:.0f} dias')
    with col3:
        mais_antigo = df_aberto['dias_aberto'].max()
        metrica('Mais Antigo', f'{mais_antigo:.0f} dias')
    with col4:
        criticos = len(df_aberto[df_aberto['prioridade'] == 'Crítica'])
        metrica('Prioridade Crítica', f'{criticos}')

    st.markdown('---')

    # Aging distribution
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.subheader('📊 Distribuição de Aging')
        fig = px.histogram(
            df_aberto, x='dias_aberto', nbins=20,
            labels={'dias_aberto': 'Dias em aberto'},
            color_discrete_sequence=['#e67e22'],
        )
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_dir:
        st.subheader('📊 Por Status')
        status_ab = df_aberto['status'].value_counts().reset_index()
        status_ab.columns = ['Status', 'Quantidade']

        fig = px.bar(
            status_ab,
            x='Quantidade',
            y='Status',
            orientation='h',
            color='Quantidade',
            color_continuous_scale='Oranges',
            text='Quantidade',
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(height=350, coloraxis_showscale=False, yaxis_title='')
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')

    # Por categoria (backlog)
    st.subheader('📁 Backlog por Categoria')
    cat_ab = df_aberto['categoria'].value_counts().head(15).reset_index()
    cat_ab.columns = ['Categoria', 'Quantidade']

    fig = px.bar(
        cat_ab,
        x='Categoria',
        y='Quantidade',
        color='Quantidade',
        color_continuous_scale='Oranges',
        text='Quantidade',
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(height=400, xaxis_tickangle=-30, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')

    # Top 20 mais antigos
    st.subheader('⏰ Tickets Mais Antigos em Aberto')
    antigos = df_aberto.nlargest(20, 'dias_aberto')[
        ['id', 'titulo', 'status', 'responsavel_atual', 'prioridade', 'dias_aberto']
    ].copy()
    antigos.columns = ['ID', 'Título', 'Status', 'Responsável', 'Prioridade', 'Dias Aberto']

    st.dataframe(
        antigos,
        hide_index=True,
        use_container_width=True,
        column_config={
            'Dias Aberto': st.column_config.NumberColumn(
                'Dias Aberto',
                format='%d dias',
            ),
        }
    )

    box_alerta(
        f'**{len(df_aberto[df_aberto["dias_aberto"] > 30])}** tickets estão em aberto há mais de 30 dias. '
        f'Priorize os mais antigos.'
    )


# ============================================================
# PÁGINA 6 — ROTEAMENTO E GARGALOS
# ============================================================
# ============================================================
# PÁGINA 6 — ROTEAMENTO E GARGALOS
# ============================================================
def pagina_roteamento(df):
    st.title('🔄 Roteamento e Gargalos')
    st.caption('Fluxo dos tickets entre analistas e identificação de gargalos.')

    conn = sqlite3.connect(CAMINHO_BANCO)
    movs = pd.read_sql('SELECT * FROM movimentacoes', conn)
    msgs = pd.read_sql('SELECT * FROM mensagens', conn)
    conn.close()

    if movs.empty:
        st.warning('⚠️ Sem movimentações. Rode o Programa5 para enriquecer.')
        return

    movs['data_movimentacao'] = pd.to_datetime(
        movs['data_movimentacao'], errors='coerce')

    movs_ok = movs.dropna(subset=['autor']).copy()

    # ---------- KPIs ----------
    total_tickets = movs_ok['ticket_id'].nunique()
    pessoas_por_ticket = movs_ok.groupby('ticket_id')['autor'].nunique()
    media_pessoas = pessoas_por_ticket.mean() if not pessoas_por_ticket.empty else 0
    msgs_total = len(msgs)
    tickets_alto = len(pessoas_por_ticket[pessoas_por_ticket >= 5])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Tickets Enriquecidos', f'{total_tickets}')
    with col2:
        st.metric('Média de Pessoas/Ticket', f'{media_pessoas:.1f}')
    with col3:
        st.metric('Mensagens Capturadas', f'{msgs_total}')
    with col4:
        st.metric('Tickets com 5+ Pessoas', f'{tickets_alto}')

    st.markdown('---')

    # ---------- Quantas pessoas por ticket ----------
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader('👥 Pessoas por Ticket')
        dist = pessoas_por_ticket.value_counts().sort_index().reset_index()
        dist.columns = ['pessoas', 'qtd']

        fig = px.bar(
            dist,
            x='pessoas',
            y='qtd',
            text='qtd',
            color='qtd',
            color_continuous_scale='Oranges',
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            height=350,
            xaxis_title='Nº de pessoas',
            yaxis_title='Nº de tickets',
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader('🔝 Top Quem Mais Movimenta')
        top_mov = movs_ok.groupby('autor').size()\
            .sort_values(ascending=False).head(10).reset_index()
        top_mov.columns = ['autor', 'qtd']
        top_mov = top_mov.iloc[::-1]  # inverte para o maior ficar em cima

        fig = px.bar(
            top_mov,
            x='qtd',
            y='autor',
            orientation='h',
            text='qtd',
            color='qtd',
            color_continuous_scale='Blues',
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            height=350,
            xaxis_title='Movimentações',
            yaxis_title='',
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('---')

    # ---------- Gargalos ----------
    st.subheader('⏱️ Maiores Gaps entre Movimentações')
    st.caption('Onde os tickets ficaram mais tempo parados')

    movs_sorted = movs_ok.sort_values(['ticket_id', 'data_movimentacao']).copy()
    movs_sorted['data_anterior'] = (
        movs_sorted.groupby('ticket_id')['data_movimentacao'].shift(1)
    )
    movs_sorted['horas_parado'] = (
        movs_sorted['data_movimentacao'] - movs_sorted['data_anterior']
    ).dt.total_seconds() / 3600

    gaps = movs_sorted.dropna(subset=['horas_parado'])
    gaps = gaps[gaps['horas_parado'] > 24].copy()
    gaps['dias_parado'] = (gaps['horas_parado'] / 24).round(1)

    if not gaps.empty:
        top_gaps = gaps.nlargest(15, 'horas_parado')[
            ['ticket_id', 'autor', 'dias_parado']
        ].copy()
        top_gaps.columns = ['Ticket', 'Quem recebeu', 'Dias parado']
        st.dataframe(top_gaps, use_container_width=True, hide_index=True)

        # Distribuição dos gaps
        st.markdown('')
        st.subheader('📊 Distribuição de Gaps')

        bins = pd.cut(
            gaps['dias_parado'],
            bins=[0, 2, 3, 7, 14, 30, 9999],
            labels=['1-2d', '2-3d', '3-7d', '7-14d', '14-30d', '30d+'],
        )
        dist = bins.value_counts().sort_index().reset_index()
        dist.columns = ['faixa', 'qtd']

        fig = px.bar(
            dist,
            x='faixa',
            y='qtd',
            text='qtd',
            color='qtd',
            color_continuous_scale='Reds',
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            height=350,
            xaxis_title='Faixa de tempo parado',
            yaxis_title='Nº de ocorrências',
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Insights
        mediana = gaps['dias_parado'].median()
        grandes = len(gaps[gaps['dias_parado'] > 7])

        if mediana > 3:
            st.warning(
                f'⚠️ Mediana de dias entre movimentações é **{mediana:.1f} dias**. '
                f'**{grandes} tickets** tiveram gap > 7 dias.'
            )
        else:
            st.success(
                f'✅ Mediana de dias entre movimentações é **{mediana:.1f} dias**.'
            )
    else:
        st.info('Sem gaps relevantes (> 1 dia) identificados.')

    st.markdown('---')

    # ---------- Mensagens ----------
    if not msgs.empty:
        st.subheader('💬 Top Quem Mais Escreve Mensagens')
        top_msg = msgs.dropna(subset=['autor']).groupby('autor').size()\
            .sort_values(ascending=False).head(10).reset_index()
        top_msg.columns = ['autor', 'qtd']
        top_msg = top_msg.iloc[::-1]

        fig = px.bar(
            top_msg,
            x='qtd',
            y='autor',
            orientation='h',
            text='qtd',
            color='qtd',
            color_continuous_scale='Greens',
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            height=350,
            xaxis_title='Mensagens',
            yaxis_title='',
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# SIDEBAR + ROTEAMENTO
# ============================================================
def main():
    # Carrega dados
    df = carregar_tickets()

    if df is None or df.empty:
        st.error('❌ Banco de dados não encontrado ou vazio.')
        st.info('Execute primeiro:\n\n```\npython src/programa4_persistir.py\n```')
        return

    df_snap = carregar_snapshots()

    # ==================== SIDEBAR — BRANDING ====================
    st.sidebar.markdown(
        '<div style="padding: 4px 6px 24px 6px;">'
        '  <div style="font-family: Fraunces, serif; font-size: 22px; '
        '              font-weight: 600; color: #eae7e1; letter-spacing: .3px;">'
        '    HELP360'
        '  </div>'
        '  <div style="font-size: 11.5px; color: #5c6270; margin-top: 4px; '
        '              letter-spacing: .4px;">'
        '    Dashboard de Análise'
        '  </div>'
        '</div>'
        '<hr style="border:none; border-top:1px solid rgba(255,255,255,.07); margin:0 0 18px 0;">',
        unsafe_allow_html=True,
    )

    # ==================== SIDEBAR — NAVEGAÇÃO ====================
    pagina = st.sidebar.radio(
        'Navegação',
        options=[
            'Visão Geral',
            'Tempo de Resposta',
            'SLA',
            'Produtividade',
            'Backlog',
            'Roteamento',
        ],
        label_visibility='collapsed',
    )

    st.sidebar.markdown(
        '<hr style="border:none; border-top:1px solid rgba(255,255,255,.07); margin:18px 0;">',
        unsafe_allow_html=True,
    )

    # ==================== SIDEBAR — FILTROS ====================
    df_filtrado = aplicar_filtros(df)

    # ==================== SIDEBAR — RODAPÉ ====================
    st.sidebar.markdown(
        f'<div style="font-size:11px; color:#5c6270; padding:10px 4px 0 4px; '
        f'border-top:1px solid rgba(255,255,255,.07); margin-top:16px;">'
        f'  Atualizado em {datetime.now():%d/%m/%Y · %H:%M}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ==================== ROTEAMENTO ====================
    if pagina == 'Visão Geral':
        pagina_visao_geral(df_filtrado, df_snap)
    elif pagina == 'Tempo de Resposta':
        pagina_tempo_resposta(df_filtrado)
    elif pagina == 'SLA':
        pagina_sla(df_filtrado)
    elif pagina == 'Produtividade':
        pagina_produtividade(df_filtrado)
    elif pagina == 'Backlog':
        pagina_backlog(df_filtrado)
    elif pagina == 'Roteamento':
        pagina_roteamento(df_filtrado)


if __name__ == '__main__':
    main()