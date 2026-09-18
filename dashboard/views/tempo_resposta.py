# ============================================================
# dashboard/pages/tempo_resposta.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
    botao_exportar,
)
from config import COR_BAR, COR_DANGER


def render(df):
    page_header('Tempo de', 'Resposta',
                'Análise dos tempos de resolução e primeira resposta.')

    # ---------- Filtra só resolvidos ----------
    df_res = df[df['dias_resolucao'].notna()].copy()

    if df_res.empty:
        callout('warning', 'Atenção', 'Sem tickets resolvidos no período.')
        return

    # ---------- KPIs ----------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Tempo Médio', f'{df_res["dias_resolucao"].mean():.1f}d')
    with col2:
        kpi('Mediana (P50)', f'{df_res["dias_resolucao"].median():.0f}d')
    with col3:
        kpi('P90', f'{df_res["dias_resolucao"].quantile(0.9):.0f}d')
    with col4:
        kpi('P99', f'{df_res["dias_resolucao"].quantile(0.99):.0f}d')

    separador()

    # ---------- Distribuição + Estatísticas ----------
    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        painel_title('Distribuição de <b>Tempo</b>')
        st.markdown(
            '<div class="page-caption" style="margin-top:-14px;">'
            'Dias até a resolução</div>',
            unsafe_allow_html=True,
        )

        fig = px.histogram(
            df_res,
            x='dias_resolucao',
            nbins=20,
            labels={'dias_resolucao': 'Dias para resolução'},
            color_discrete_sequence=[COR_BAR],
        )
        fig = aplicar_tema_plotly(fig, altura=300)
        st.plotly_chart(fig, use_container_width=True,
                        config={'displayModeBar': False})

    with col_dir:
        painel_title('Resumo <b>Estatístico</b>')
        stats = pd.DataFrame({
            'Métrica': ['Mínimo', 'P25', 'Mediana', 'P75', 'P90', 'Máximo'],
            'Dias': [
                f'{df_res["dias_resolucao"].min():.0f}',
                f'{df_res["dias_resolucao"].quantile(0.25):.0f}',
                f'{df_res["dias_resolucao"].median():.0f}',
                f'{df_res["dias_resolucao"].quantile(0.75):.0f}',
                f'{df_res["dias_resolucao"].quantile(0.90):.0f}',
                f'{df_res["dias_resolucao"].max():.0f}',
            ],
        })
        st.dataframe(stats, hide_index=True, use_container_width=True)

    separador()

    # ---------- Por categoria ----------
    painel_title('Tempo Médio por <b>Categoria</b>')
    cat_tempo = df_res.groupby('categoria').agg(
        total=('id', 'count'),
        dias_medio=('dias_resolucao', 'mean'),
        dias_1a=('dias_1a_resposta', 'mean'),
    ).reset_index()
    cat_tempo = cat_tempo[cat_tempo['total'] >= 3]
    cat_tempo = cat_tempo.sort_values('dias_medio')

    if not cat_tempo.empty:
        hbar_list([
            {'label': r['categoria'],
             'value': float(r['dias_medio']),
             'formatted': f'{r["dias_medio"]:.1f}d',
             'accent': r['dias_medio'] > 10}
            for _, r in cat_tempo.iterrows()
        ])

        pior = cat_tempo.iloc[-1]
        melhor = cat_tempo.iloc[0]
        callout(
            'info', 'Insight',
            f'<b>{pior["categoria"]}</b> é a categoria mais lenta '
            f'(<b>{pior["dias_medio"]:.1f} dias</b>). '
            f'Já <b>{melhor["categoria"]}</b> resolve em '
            f'<b>{melhor["dias_medio"]:.1f} dias</b>.'
        )

    separador()

    # ---------- Por prioridade ----------
    painel_title('Tempo Médio por <b>Prioridade</b>')
    prio_tempo = df_res.groupby('prioridade').agg(
        total=('id', 'count'),
        dias_medio=('dias_resolucao', 'mean'),
    ).reset_index()

    ordem = ['Crítica', 'Alta', 'Média', 'Baixa-1', 'Baixa-2', 'Baixa-3']
    prio_tempo['ordem'] = prio_tempo['prioridade'].map(
        {p: i for i, p in enumerate(ordem)}
    ).fillna(99)
    prio_tempo = prio_tempo.sort_values('ordem')

    hbar_list([
        {'label': r['prioridade'],
         'value': float(r['dias_medio']),
         'formatted': f'{r["dias_medio"]:.1f}d',
         'accent': r['prioridade'] == 'Crítica'}
        for _, r in prio_tempo.iterrows()
    ])

    # Alerta de prioridade invertida
    crit = prio_tempo[prio_tempo['prioridade'] == 'Crítica']['dias_medio'].values
    alta = prio_tempo[prio_tempo['prioridade'] == 'Alta']['dias_medio'].values
    if len(crit) > 0 and len(alta) > 0 and crit[0] > alta[0]:
        callout(
            'warning', 'Atenção',
            f'Prioridade <b>Crítica</b> está demorando mais que <b>Alta</b> '
            f'({crit[0]:.1f} vs {alta[0]:.1f} dias). Verifique a triagem.'
        )

    separador()
    
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df_res, 'tempo_resposta', key='export_tempo_resposta')