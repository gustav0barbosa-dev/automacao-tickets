# ============================================================
# dashboard/pages/visao_geral.py
# ============================================================

import streamlit as st
import plotly.graph_objects as go

from components import (
    kpi, hbar_list, callout, painel_title,
    separador, page_header, aplicar_tema_plotly,
    botao_exportar, legenda_grafico, info_grafico,
    filtrar_outliers, alerta_fantasmas, 
)
from config import COR_GOLD, COR_BAR


def render(df):
    page_header('Visão', 'Geral',
                'Panorama geral dos tickets no período selecionado.')

    total = len(df)
    resolvidos = len(df[df['status'].isin(['Resolvido', 'Fechado'])])
    em_aberto = len(df[~df['status'].isin(
        ['Resolvido', 'Fechado', 'Cancelado', 'Duplicado'])])

    df_sla = df[df['sla_status'].isin(['cumprido', 'estourado'])]
    cumpridos = len(df_sla[df_sla['sla_status'] == 'cumprido'])
    estourados = len(df_sla[df_sla['sla_status'] == 'estourado'])
    total_sla = cumpridos + estourados
    perc_sla = (cumpridos / total_sla * 100) if total_sla else 0

    df_aberto = df[~df['status'].isin(
        ['Resolvido', 'Fechado', 'Cancelado', 'Duplicado'])]
    aging = df_aberto['dias_aberto'].mean() if not df_aberto.empty else 0

    # ---------- KPIs ----------
    total = len(df)
    resolvidos = len(df[df['status'].isin(['Resolvido', 'Fechado'])])
    em_aberto = len(df[~df['status'].isin(['Resolvido', 'Fechado', 'Cancelado', 'Duplicado'])])

    # SLA
    df_sla = df[df['sla_status'].isin(['cumprido', 'estourado'])]
    cumpridos = len(df_sla[df_sla['sla_status'] == 'cumprido'])
    estourados = len(df_sla[df_sla['sla_status'] == 'estourado'])
    total_sla = cumpridos + estourados
    perc_sla = (cumpridos / total_sla * 100) if total_sla else 0

    # Aging com filtro de outlier
    df_aberto = df[~df['status'].isin(['Resolvido', 'Fechado', 'Cancelado', 'Duplicado'])].copy()
    df_aberto_clean, n_outliers = filtrar_outliers(df_aberto, 'dias_aberto')
    aging = df_aberto_clean['dias_aberto'].mean() if not df_aberto_clean.empty else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        kpi('Total de Tickets', f'{total}')
    with col2:
        perc_res = f'{resolvidos/total*100:.0f}%' if total else '—'
        kpi('Resolvidos', f'{resolvidos}', pill=perc_res, pill_tipo='positive')
    with col3:
        kpi('Em Aberto', f'{em_aberto}')
    with col4:
        perc_geral = (cumpridos / total * 100) if total else 0
        kpi('% SLA (resolvidos)', f'{perc_sla:.0f}%',
            pill=f'{perc_geral:.0f}% do total',
            pill_tipo='negative' if perc_geral < 50 else 'neutral',
            ajuda=f'{cumpridos} cumpridos · {estourados} estourados')
    with col5:
        kpi('Aging Médio', f'{aging:.0f}d',
            pill='Alto' if aging > 15 else 'OK',
            pill_tipo='negative' if aging > 15 else 'positive',
            ajuda=f'Exclui {n_outliers} tickets > 365 dias' if n_outliers else None)

    # Alerta de fantasmas
    alerta_fantasmas(df_aberto)

    separador()

    # ---------- Gráficos ----------
    col_a, col_b, col_c = st.columns([1, 1, 1])

    with col_a:
        painel_title('Tickets por <b>Status</b>')
        sc = df['status'].value_counts()
        hbar_list([
            {'label': s, 'value': int(v), 'formatted': str(v)}
            for s, v in sc.items()
        ])

    with col_b:
        painel_title('Tickets por <b>Prioridade</b>')
        pc = df['prioridade'].value_counts()
        ordem = ['Crítica', 'Alta', 'Média', 'Baixa-1', 'Baixa-2', 'Baixa-3']
        items = [
            {'label': p, 'value': int(pc[p]),
             'formatted': str(pc[p]),
             'accent': p == 'Crítica'}
            for p in ordem if p in pc.index
        ]
        hbar_list(items)

    with col_c:
        painel_title('Tickets Criados · <b>Últimos Meses</b>')
        df_trend = df[df['criado_data'].notna()].copy()
        if not df_trend.empty:
            df_trend['mes'] = df_trend['criado_data'].dt.to_period('M').astype(str)
            serie = df_trend.groupby('mes').size().tail(6)
            fig = go.Figure(go.Scatter(
                x=serie.index, y=serie.values,
                mode='lines+markers',
                line=dict(color=COR_GOLD, width=2),
                marker=dict(color=COR_GOLD, size=6),
                fill='tozeroy',
                fillcolor='rgba(201,166,102,.08)',
            ))
            fig = aplicar_tema_plotly(fig, altura=240)
            st.plotly_chart(fig, use_container_width=True,
                            config={'displayModeBar': False})

    separador()


    # ---------- Top categorias ----------
    painel_title('Tickets por <b>Categoria</b>')
    cc = df['categoria'].value_counts().head(10)
    hbar_list([
        {'label': c, 'value': int(v), 'formatted': str(v)}
        for c, v in cc.items()
    ])

    separador()


    st.markdown('### Insights')

    if perc_sla >= 90:
        callout('success', 'OK', f'SLA dos resolvidos está em <b>{perc_sla:.1f}%</b>.')
    elif perc_sla >= 70:
        callout('info', 'Insight', f'SLA dos resolvidos está em <b>{perc_sla:.1f}%</b>.')
    else:
        callout('warning', 'Atenção',
                f'SLA dos resolvidos está em <b>{perc_sla:.1f}%</b> — abaixo da meta.')

    if em_aberto > total * 0.3:
        callout('warning', 'Atenção',
                f'<b>{em_aberto} de {total} tickets</b> ({em_aberto/total*100:.0f}%) '
                f'estão em aberto.')

    if aging > 15:
        callout('warning', 'Atenção',
                f'Aging médio em aberto é <b>{aging:.0f} dias</b>.')

    esquecidos = len(df_aberto[df_aberto['dias_aberto'] > 30])
    if esquecidos > 0:
        callout('warning', 'Atenção',
                f'<b>{esquecidos} tickets</b> estão em aberto há mais de 30 dias.')

    separador()
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df, 'visao_geral', key='export_visao_geral')