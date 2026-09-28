# ============================================================
# dashboard/views/visao_geral.py — Visão Geral (refatorado)
# ============================================================

import streamlit as st
import plotly.graph_objects as go

from components import (
    kpi, hbar_list, callout, painel_title,
    separador, aplicar_tema_plotly, botao_exportar,
    legenda_grafico, info_grafico, filtrar_outliers,
    alerta_fantasmas, chart_card, global_header,
)
from lucide import lucide
from config import COR_GOLD, COR_BAR


def render(df):
    # ==================== HEADER GLOBAL ====================
    global_header(
        'Visão Geral',
        'Panorama geral dos tickets no período selecionado.',
        usuario=st.session_state.get('usuario'),
    )

    # ==================== CÁLCULOS ====================
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
        ['Resolvido', 'Fechado', 'Cancelado', 'Duplicado'])].copy()
    df_aberto_clean, n_outliers = filtrar_outliers(df_aberto, 'dias_aberto')
    aging = df_aberto_clean['dias_aberto'].mean() if not df_aberto_clean.empty else 0

    # ==================== KPIs ====================
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        kpi('Total', f'{total}', icone='inbox')
    with col2:
        perc_res = f'{resolvidos/total*100:.0f}%' if total else '—'
        kpi('Resolvidos', f'{resolvidos}', pill=perc_res,
            pill_tipo='positive', icone='check-circle')
    with col3:
        kpi('Em Aberto', f'{em_aberto}', icone='clock')
    with col4:
        perc_geral = (cumpridos / total * 100) if total else 0
        kpi('SLA', f'{perc_sla:.0f}%',
            pill=f'{perc_geral:.0f}% do total',
            pill_tipo='negative' if perc_geral < 50 else 'neutral',
            ajuda=f'{cumpridos} cumpridos · {estourados} estourados',
            icone='target')
    with col5:
        kpi('Aging', f'{aging:.0f}d',
            pill='Alto' if aging > 15 else 'OK',
            pill_tipo='negative' if aging > 15 else 'positive',
            ajuda=f'Exclui {n_outliers} > 365d' if n_outliers else None,
            icone='trending-up')

    # Alerta de fantasmas
    alerta_fantasmas(df_aberto)

    # ==================== GRÁFICOS ====================
    st.markdown('')  # respiro

    col_a, col_b = st.columns(2)

    with col_a:
        with chart_card('Tickets por Status',
                        'Distribuição atual no período filtrado',
                        icone='pie-chart'):
            sc = df['status'].value_counts()
            hbar_list([
                {'label': s, 'value': int(v), 'formatted': str(v)}
                for s, v in sc.items()
            ])

    with col_b:
        with chart_card('Tickets por Prioridade',
                        'Volume por criticidade',
                        icone='bar-chart'):
            pc = df['prioridade'].value_counts()
            ordem = ['Crítica', 'Alta', 'Média', 'Baixa-1', 'Baixa-2', 'Baixa-3']
            items = [
                {'label': p, 'value': int(pc[p]),
                 'formatted': str(pc[p]),
                 'accent': p == 'Crítica'}
                for p in ordem if p in pc.index
            ]
            hbar_list(items)

    # ==================== EVOLUÇÃO ====================
    with chart_card('Volume de Tickets',
                    'Evolução dos últimos 6 meses',
                    icone='chart-line'):
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
            fig = aplicar_tema_plotly(fig, altura=260)
            st.plotly_chart(fig, use_container_width=True,
                            config={'displayModeBar': False})

    # ==================== CATEGORIAS ====================
    with chart_card('Tickets por Categoria',
                    'Top 10 categorias por volume',
                    icone='bar-chart'):
        cc = df['categoria'].value_counts().head(10)
        hbar_list([
            {'label': c, 'value': int(v), 'formatted': str(v)}
            for c, v in cc.items()
        ])

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
        if perc_sla >= 90:
            _insight_card('success', 'SLA', f'{perc_sla:.0f}%', 'Dentro da meta')
        elif perc_sla >= 70:
            _insight_card('info', 'SLA', f'{perc_sla:.0f}%', 'Atenção')
        else:
            _insight_card('warning', 'SLA', f'{perc_sla:.0f}%', 'Abaixo da meta')

    with col_i2:
        esquecidos = len(df_aberto[df_aberto['dias_aberto'] > 30])
        if esquecidos > 0:
            _insight_card('warning', 'Backlog', f'{esquecidos}', '> 30 dias')
        else:
            _insight_card('success', 'Backlog', '0', 'Nenhum > 30d')

    with col_i3:
        if aging > 15:
            _insight_card('warning', 'Aging', f'{aging:.0f}d', 'Alto')
        else:
            _insight_card('success', 'Aging', f'{aging:.0f}d', 'OK')

    # ==================== EXPORTAR ====================
    separador()
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df, 'visao_geral', key='export_visao_geral')


def _insight_card(tipo, titulo, valor, detalhe):
    """Card compacto de insight com ação."""
    cores = {
        'success': ('#7fc99b', 'check-circle'),
        'warning': ('#d9ac53', 'alert-triangle'),
        'info':    ('#8b96a8', 'info'),
    }
    cor, icone = cores.get(tipo, ('#8b96a8', 'info'))

    st.markdown(
        f'<div style="background:#1b2029;border:1px solid rgba(255,255,255,.07);'
        f'border-radius:12px;padding:16px 18px;height:100%;'
        f'transition:border-color .2s ease;'
        f'border-left:3px solid {cor};">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
        f'<span style="color:{cor};">{lucide(icone, 16)}</span>'
        f'<span style="font-size:11px;color:#5c6270;letter-spacing:.8px;'
        f'text-transform:uppercase;font-weight:600;">{titulo}</span>'
        f'</div>'
        f'<div style="font-family:Fraunces,serif;font-size:24px;'
        f'font-weight:600;color:#eae7e1;line-height:1.1;">{valor}</div>'
        f'<div style="font-size:12px;color:#9299a6;margin-top:6px;">{detalhe}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )