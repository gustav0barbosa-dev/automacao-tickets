# ============================================================
# dashboard/pages/tempo_resposta.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
    botao_exportar, legenda_grafico, info_grafico,
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
    df_res_sem_outlier = df_res[df_res['dias_resolucao'] <= 365].copy()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Tempo Médio', f'{df_res_sem_outlier["dias_resolucao"].mean():.1f}d',
            ajuda=f'Exclui {len(df_res) - len(df_res_sem_outlier)} outliers (> 365d)')
    with col2:
        kpi('Mediana (P50)', f'{df_res_sem_outlier["dias_resolucao"].median():.0f}d')
    with col3:
        kpi('P90', f'{df_res_sem_outlier["dias_resolucao"].quantile(0.9):.0f}d')
    with col4:
        kpi('P99', f'{df_res_sem_outlier["dias_resolucao"].quantile(0.99):.0f}d')

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

        legenda_grafico([
            {'cor': COR_BAR, 'label': 'Frequência de tickets', 'tipo': 'barra'},
        ])
        info_grafico(
            'O <b>eixo X</b> mostra os dias até a resolução. '
            'O <b>eixo Y</b> mostra quantos tickets levaram aquele tempo. '
            'A maioria se concentra à esquerda (rápido) ou à direita (lento).'
        )

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
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Excluindo outliers (> 365 dias)'
                '</div>',
                unsafe_allow_html=True)

    cat_tempo = df_res_sem_outlier.groupby('categoria').agg(
        total=('id', 'count'),
        dias_medio=('dias_resolucao', 'mean'),
        dias_mediana=('dias_resolucao', 'median'),
    ).reset_index()
    cat_tempo = cat_tempo[cat_tempo['total'] >= 3]
    cat_tempo = cat_tempo.sort_values('dias_medio')

    if not cat_tempo.empty:
        hbar_list([
            {'label': f'{r["categoria"][:30]} · {int(r["total"])} tickets',
             'value': float(r['dias_medio']),
             'formatted': f'{r["dias_medio"]:.1f}d',
             'accent': r['dias_medio'] > 15}
            for _, r in cat_tempo.iterrows()
        ])

        pior = cat_tempo.iloc[-1]
        melhor = cat_tempo.iloc[0]
        callout(
            'info', 'Insight',
            f'<b>{pior["categoria"]}</b> é a mais lenta '
            f'(<b>{pior["dias_medio"]:.1f} dias</b>). '
            f'Já <b>{melhor["categoria"]}</b> resolve em '
            f'<b>{melhor["dias_medio"]:.1f} dias</b>.'
        )

    separador()

    # ---------- Por prioridade ----------
    painel_title('Tempo Médio por <b>Prioridade</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Excluindo tickets com mais de 365 dias (outliers)'
                '</div>',
                unsafe_allow_html=True)

    # Filtra outliers
    df_res_sem_outlier = df_res[df_res['dias_resolucao'] <= 365].copy()

    prio_tempo = df_res_sem_outlier.groupby('prioridade').agg(
        total=('id', 'count'),
        dias_medio=('dias_resolucao', 'mean'),
        dias_mediana=('dias_resolucao', 'median'),
    ).reset_index()

    # Ordenação
    ordem = ['Crítica', 'Urgente', 'Alta', 'Média', 'Média-1', 'Média-2',
             'Baixa', 'Baixa-1', 'Baixa-2', 'Baixa-3']
    prio_tempo['ordem'] = prio_tempo['prioridade'].map(
        {p: i for i, p in enumerate(ordem)}
    ).fillna(99)
    prio_tempo = prio_tempo.sort_values('ordem')

    hbar_list([
        {'label': f'{r["prioridade"]} · média: {r["dias_medio"]:.1f}d · mediana: {r["dias_mediana"]:.0f}d',
         'value': float(r['dias_medio']),
         'formatted': f'{r["dias_medio"]:.1f}d',
         'accent': r['prioridade'] in ['Crítica', 'Urgente']}
        for _, r in prio_tempo.iterrows()
    ])

    # Comparação com/sem outliers
    df_medio_com_outlier = df_res.groupby('prioridade')['dias_resolucao'].mean()
    df_medio_sem_outlier = prio_tempo.set_index('prioridade')['dias_medio']

    diff = (df_medio_com_outlier - df_medio_sem_outlier).dropna()
    if not diff.empty and diff.abs().max() > 100:
        pior = diff.idxmax()
        callout('warning', 'Atenção',
                f'A prioridade <b>{pior}</b> tem média de '
                f'<b>{df_medio_com_outlier[pior]:.0f} dias</b> com outliers, '
                f'mas apenas <b>{df_medio_sem_outlier[pior]:.1f} dias</b> sem eles. '
                f'Isso indica <b>tickets muito antigos</b> puxando a média.')

    info_grafico(
        'Excluindo tickets com mais de <b>365 dias</b> entre criação e resolução. '
        'A <b>média</b> (barra) é sensível a outliers; a <b>mediana</b> (no texto) é mais robusta. '
        'Se a média estiver muito acima da mediana, existem tickets antigos distorcendo o número.'
    )

    separador()
    
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df_res, 'tempo_resposta', key='export_tempo_resposta')