# ============================================================
# dashboard/views/backlog.py — refatorado (Fase 5)
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

from components import (
    kpi, callout, separador, hbar_list, painel_title,
    aplicar_tema_plotly, botao_exportar, legenda_grafico,
    info_grafico, chart_card, card_com_tabela, card_com_barras,
    global_header, empty_state, insight_card,
    filtrar_outliers, alerta_fantasmas,
    BADGES_PRIORIDADE, BADGES_STATUS,
)
from lucide import lucide
from config import COR_WARNING, COR_DANGER, STATUS_FECHADOS


def render(df):
    # ==================== HEADER ====================
    global_header(
        'Backlog Atual',
        'Tickets em aberto, aging e prioritários.',
        usuario=st.session_state.get('usuario'),
    )

    # ---------- Filtra em aberto ----------
    df_aberto = df[~df['status'].isin(STATUS_FECHADOS)].copy()

    if df_aberto.empty:
        empty_state(
            titulo='Sem tickets em aberto',
            descricao='Todos os tickets foram resolvidos no período. 🎉',
            icone='check-circle',
        )
        return

    # Filtra outliers
    df_aberto_clean, n_outliers = filtrar_outliers(df_aberto, 'dias_aberto')

    # ---------- Métricas ----------
    aging = df_aberto_clean['dias_aberto'].mean() if not df_aberto_clean.empty else 0
    mais_antigo = df_aberto_clean['dias_aberto'].max() if not df_aberto_clean.empty else 0
    criticos = len(df_aberto[df_aberto['prioridade'] == 'Crítica'])
    antigos_30 = len(df_aberto_clean[df_aberto_clean['dias_aberto'] > 30])

    # ==================== KPIs ====================
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Total em Aberto', f'{len(df_aberto)}', icone='inbox')
    with col2:
        kpi('Aging Médio', f'{aging:.0f}d',
            pill='Alto' if aging > 15 else 'OK',
            pill_tipo='negative' if aging > 15 else 'positive',
            ajuda=f'Exclui {n_outliers} > 365d' if n_outliers else None,
            icone='clock')
    with col3:
        kpi('Mais Antigo', f'{mais_antigo:.0f}d',
            pill='⚠️ > 30d' if mais_antigo > 30 else 'OK',
            pill_tipo='negative' if mais_antigo > 30 else 'positive',
            icone='alert-triangle')
    with col4:
        kpi('Prioridade Crítica', f'{criticos}',
            pill='Atenção' if criticos > 0 else 'OK',
            pill_tipo='negative' if criticos > 0 else 'positive',
            icone='zap')

    # Alerta de fantasmas
    alerta_fantasmas(df_aberto)

    # ==================== DISTRIBUIÇÃO DE AGING + POR STATUS ====================
    col_a, col_b = st.columns([2, 1])

    with col_a:
        with chart_card('Distribuição de Aging',
                        'Dias em aberto',
                        icone='bar-chart'):
            fig = px.histogram(
                df_aberto,
                x='dias_aberto',
                nbins=20,
                labels={'dias_aberto': 'Dias em aberto'},
                color_discrete_sequence=[COR_WARNING],
            )
            fig = aplicar_tema_plotly(fig, altura=280)
            st.plotly_chart(fig, use_container_width=True,
                            config={'displayModeBar': False})

            legenda_grafico([
                {'cor': COR_WARNING, 'label': 'Tickets por faixa de dias', 'tipo': 'barra'},
            ])
            info_grafico(
                'O gráfico mostra quantos tickets estão em aberto em cada faixa de dias. '
                'Barras à direita indicam <b>tickets antigos</b> que precisam de atenção.'
            )

    with col_b:
        sc = df_aberto['status'].value_counts()
        card_com_barras(
            titulo='Por Status',
            descricao='Distribuição atual',
            icone='inbox',
            items=[
                {'label': s, 'value': int(v), 'formatted': str(v)}
                for s, v in sc.items()
            ],
        )

    # ==================== BACKLOG POR CATEGORIA ====================
    cc = df_aberto['categoria'].value_counts().head(10)

    if not cc.empty:
        card_com_barras(
            titulo='Backlog por Categoria',
            descricao='Top 10 categorias com mais tickets em aberto',
            icone='bar-chart',
            items=[
                {'label': c, 'value': int(v), 'formatted': str(v)}
                for c, v in cc.items()
            ],
        )

    # ==================== BACKLOG POR RESPONSÁVEL ====================
    resp_ab = df_aberto[
        df_aberto['responsavel_atual'].notna() &
        (df_aberto['responsavel_atual'] != 'Não informado')
    ]['responsavel_atual'].value_counts().head(10)

    if not resp_ab.empty:
        card_com_barras(
            titulo='Backlog por Responsável',
            descricao='Top 10 analistas com mais tickets em aberto',
            icone='users',
            items=[
                {'label': r,
                 'value': int(v),
                 'formatted': str(v),
                 'accent': v >= 10}
                for r, v in resp_ab.items()
            ],
        )

    # ==================== AGING POR FAIXA ====================
    bins = pd.cut(
        df_aberto['dias_aberto'],
        bins=[-1, 5, 10, 15, 20, 30, 9999],
        labels=['0-5d', '6-10d', '11-15d', '16-20d', '21-30d', '30d+'],
    )
    dist = bins.value_counts().sort_index().reset_index()
    dist.columns = ['faixa', 'qtd']

    if not dist.empty:
        card_com_barras(
            titulo='Aging por Faixa',
            descricao='Distribuição dos tickets por tempo em aberto',
            icone='clock',
            items=[
                {'label': r['faixa'],
                 'value': int(r['qtd']),
                 'formatted': str(int(r['qtd'])),
                 'accent': r['faixa'] in ['21-30d', '30d+']}
                for _, r in dist.iterrows()
            ],
        )

    # ==================== TOP 20 MAIS ANTIGOS ====================
    antigos = df_aberto.nlargest(20, 'dias_aberto')[
        ['id', 'titulo', 'status', 'responsavel_atual', 'prioridade', 'dias_aberto']
    ].copy()

    card_com_tabela(
        titulo='Tickets Mais Antigos em Aberto',
        descricao='Top 20 por tempo em aberto',
        icone='alert-triangle',
        df=antigos,
        colunas=[
            {'campo': 'id', 'label': 'ID', 'tipo': 'num'},
            {'campo': 'titulo', 'label': 'Título', 'tipo': 'texto',
             'truncate': True},
            {'campo': 'status', 'label': 'Status', 'tipo': 'badge',
             'badge_map': BADGES_STATUS},
            {'campo': 'prioridade', 'label': 'Prioridade', 'tipo': 'badge',
             'badge_map': BADGES_PRIORIDADE},
            {'campo': 'responsavel_atual', 'label': 'Responsável',
             'tipo': 'texto'},
            {'campo': 'dias_aberto', 'label': 'Dias', 'tipo': 'num'},
        ],
    )

    # ==================== INSIGHTS ====================
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'margin:24px 0 14px 0;">'
        f'<span style="color:#c9a666;">{lucide("alert-triangle", 18)}</span>'
        f'<span style="font-family:Fraunces,serif;font-size:18px;font-weight:600;">'
        f'Insights e Alertas</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_i1, col_i2, col_i3 = st.columns(3)

    with col_i1:
        insight_card(
            'warning' if antigos_30 > 0 else 'success',
            'Antigos > 30d',
            f'{antigos_30}',
            'tickets',
        )

    with col_i2:
        if aging > 15:
            insight_card('warning', 'Aging Médio', f'{aging:.0f}d', 'Acima do ideal (15d)')
        elif aging > 8:
            insight_card('info', 'Aging Médio', f'{aging:.0f}d', 'Dentro do aceitável')
        else:
            insight_card('success', 'Aging Médio', f'{aging:.0f}d', 'Excelente')

    with col_i3:
        if not resp_ab.empty:
            top_resp, top_qtd = resp_ab.index[0], resp_ab.iloc[0]
            insight_card(
                'warning' if top_qtd >= 15 else 'info',
                'Top Responsável',
                f'{top_qtd}',
                top_resp[:30],
            )

    # ==================== EXPORTAR ====================
    separador()
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df_aberto, 'backlog', key='export_backlog')