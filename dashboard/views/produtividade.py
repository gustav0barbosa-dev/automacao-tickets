# ============================================================
# dashboard/views/produtividade.py — refatorado (Fase 5)
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from components import (
    kpi, callout, separador, hbar_list, painel_title,
    aplicar_tema_plotly, botao_exportar, legenda_grafico,
    info_grafico, chart_card, card_com_tabela, global_header,
    empty_state, insight_card,
    BADGES_PRIORIDADE, BADGES_STATUS, card_com_barras,
)
from lucide import lucide
from config import COR_BAR, COR_DANGER, COR_TEXT_SEC


def render(df):
    # ==================== HEADER ====================
    global_header(
        'Produtividade por Responsável',
        'Análise de volume e tempo por analista.',
        usuario=st.session_state.get('usuario'),
    )

    # ---------- Filtra responsáveis válidos ----------
    df_resp = df[
        df['responsavel_atual'].notna() &
        (df['responsavel_atual'] != '') &
        (df['responsavel_atual'] != 'Não informado')
    ].copy()

    if df_resp.empty:
        empty_state(
            titulo='Sem responsáveis identificados',
            descricao='Nenhum ticket tem responsável no período selecionado.',
            icone='users',
        )
        return

    # ---------- Filtra outliers ----------
    df_resp_clean = df_resp[df_resp['dias_resolucao'] <= 365].copy()

    # ---------- Agrega por responsável ----------
    agg = df_resp_clean.groupby('responsavel_atual').agg(
        total=('id', 'count'),
        resolvidos=('status', lambda x: x.isin(['Resolvido', 'Fechado']).sum()),
        em_aberto=('status', lambda x: (
            ~x.isin(['Resolvido', 'Fechado', 'Cancelado'])
        ).sum()),
        dias_medio=('dias_resolucao', 'mean'),
    ).reset_index()
    agg.columns = ['Responsável', 'Total', 'Resolvidos', 'Em Aberto', 'Dias Médio']
    agg['% Resolução'] = (agg['Resolvidos'] / agg['Total'] * 100).round(1)
    agg['Dias Médio'] = agg['Dias Médio'].round(1)
    agg = agg.sort_values('Total', ascending=False)

    # ---------- KPIs ----------
    col1, col2, col3 = st.columns(3)
    with col1:
        kpi('Analistas Ativos', f'{len(agg)}', icone='users')
    with col2:
        kpi('Total de Tickets', f'{agg["Total"].sum()}', icone='inbox')
    with col3:
        kpi('Média por Analista', f'{agg["Total"].mean():.0f}',
            pill='tickets', icone='activity')

    # ==================== RANKING POR VOLUME ====================
    items_ranking = [
        {'label': r['Responsável'],
         'value': int(r['Total']),
         'formatted': str(int(r['Total'])),
         'accent': pd.notna(r['Dias Médio']) and r['Dias Médio'] > 9}
        for _, r in agg.iterrows()
    ]

    card_com_barras(
        titulo='Ranking por Volume',
        descricao='Barras vermelhas = tempo médio acima de 9 dias',
        icone='bar-chart',
        items=items_ranking,
    )

    # ==================== VOLUME VS TEMPO ====================
    agg_plot = agg.dropna(subset=['Dias Médio'])
    if not agg_plot.empty:
        with chart_card('Volume vs. Tempo Médio',
                        'Tamanho do ponto = tickets em aberto · Vermelho = acima de 9 dias',
                        icone='activity'):
            fig = go.Figure()
            for _, r in agg_plot.iterrows():
                acima = r['Dias Médio'] > 9
                fig.add_trace(go.Scatter(
                    x=[r['Total']],
                    y=[r['Dias Médio']],
                    mode='markers+text',
                    marker=dict(
                        size=max(12, r['Em Aberto'] * 1.6),
                        color='rgba(224,134,122,.55)' if acima else 'rgba(139,150,168,.5)',
                        line=dict(color=COR_DANGER if acima else COR_BAR, width=1),
                    ),
                    text=[r['Responsável'].split()[0]],
                    textposition='top center',
                    textfont=dict(size=10, color=COR_TEXT_SEC),
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{r['Responsável']}</b><br>"
                        f"Total: {r['Total']}<br>"
                        f"Dias médio: {r['Dias Médio']:.1f}<br>"
                        f"Em aberto: {r['Em Aberto']}<extra></extra>"
                    ),
                ))

            fig.update_xaxes(title_text='Tickets atribuídos')
            fig.update_yaxes(title_text='Dias médio de resolução')
            fig = aplicar_tema_plotly(fig, altura=380)
            st.plotly_chart(fig, use_container_width=True,
                            config={'displayModeBar': False})

            legenda_grafico([
                {'cor': '#8b96a8', 'label': 'OK (até 9 dias)'},
                {'cor': '#e0867a', 'label': 'Lento (acima de 9 dias)'},
            ])
            info_grafico(
                'Cada bolha é um <b>analista</b>. '
                '<b>X</b> = tickets atribuídos · <b>Y</b> = dias médios de resolução · '
                '<b>Tamanho</b> = tickets em aberto.'
            )

    # ==================== TABELA DETALHADA ====================
    agg_tabela = agg.copy()
    agg_tabela = agg_tabela.rename(columns={
        'Total': 'Total',
        'Resolvidos': 'Resolvidos',
        'Em Aberto': 'Em Aberto',
        'Dias Médio': 'Dias Médio',
    })

    card_com_tabela(
        titulo='Tabela Detalhada',
        descricao='Produtividade por analista',
        icone='bar-chart',
        df=agg_tabela,
        colunas=[
            {'campo': 'Responsável', 'label': 'Responsável', 'tipo': 'texto'},
            {'campo': 'Total', 'label': 'Total', 'tipo': 'num'},
            {'campo': 'Resolvidos', 'label': 'Resolvidos', 'tipo': 'num'},
            {'campo': 'Em Aberto', 'label': 'Em Aberto', 'tipo': 'num'},
            {'campo': 'Dias Médio', 'label': 'Dias Médio', 'tipo': 'num'},
            {'campo': '% Resolução', 'label': '% Resolução', 'tipo': 'num'},
        ],
    )

    # ==================== ALERTAS DE SOBRECARGA ====================
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'margin:24px 0 14px 0;">'
        f'<span style="color:#c9a666;">{lucide("alert-triangle", 18)}</span>'
        f'<span style="font-family:Fraunces,serif;font-size:18px;font-weight:600;">'
        f'Alertas de Sobrecarga</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_a1, col_a2, col_a3 = st.columns(3)

    # Conta alertas
    sobrecarregados = agg[agg['Em Aberto'] >= 10]
    lentos = agg[(agg['Dias Médio'] > 9) & (agg['Em Aberto'] < 10)]

    with col_a1:
        n = len(sobrecarregados)
        insight_card(
            'warning' if n > 0 else 'success',
            'Sobrecarga',
            f'{n}',
            'analista(s) com 10+ em aberto',
        )
    with col_a2:
        n = len(lentos)
        insight_card(
            'warning' if n > 0 else 'success',
            'Lentidão',
            f'{n}',
            'analista(s) acima de 9 dias',
        )
    with col_a3:
        n = len(agg)
        insight_card(
            'info',
            'Total Analistas',
            f'{n}',
            'ativos no período',
        )

    # ==================== EXPORTAR ====================
    separador()
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(agg, 'produtividade', key='export_produtividade')