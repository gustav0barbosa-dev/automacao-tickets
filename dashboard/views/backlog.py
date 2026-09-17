# ============================================================
# dashboard/pages/backlog.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
)
from config import COR_WARNING, COR_DANGER, STATUS_FECHADOS


def render(df):
    page_header('Backlog', 'Atual',
                'Tickets em aberto, aging e prioritários.')

    # ---------- Filtra em aberto ----------
    df_aberto = df[~df['status'].isin(STATUS_FECHADOS)].copy()

    if df_aberto.empty:
        callout('success', 'OK', 'Sem tickets em aberto!')
        return

    # ---------- Métricas ----------
    aging = df_aberto['dias_aberto'].mean()
    mais_antigo = df_aberto['dias_aberto'].max()
    criticos = len(df_aberto[df_aberto['prioridade'] == 'Crítica'])
    antigos_30 = len(df_aberto[df_aberto['dias_aberto'] > 30])

    # ---------- KPIs ----------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Total em Aberto', f'{len(df_aberto)}')
    with col2:
        kpi('Aging Médio', f'{aging:.0f}d',
            pill='Alto' if aging > 15 else 'OK',
            pill_tipo='negative' if aging > 15 else 'positive')
    with col3:
        kpi('Mais Antigo', f'{mais_antigo:.0f}d',
            pill='⚠️ > 30d' if mais_antigo > 30 else 'OK',
            pill_tipo='negative' if mais_antigo > 30 else 'positive')
    with col4:
        kpi('Prioridade Crítica', f'{criticos}',
            pill='Atenção' if criticos > 0 else 'OK',
            pill_tipo='negative' if criticos > 0 else 'positive')

    separador()

    # ---------- Distribuição de Aging + Por Status ----------
    col_a, col_b = st.columns([2, 1])

    with col_a:
        painel_title('Distribuição de <b>Aging</b>')
        st.markdown(
            '<div class="page-caption" style="margin-top:-14px;">'
            'Dias em aberto</div>',
            unsafe_allow_html=True,
        )

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

    with col_b:
        painel_title('Por <b>Status</b>')
        sc = df_aberto['status'].value_counts()
        hbar_list([
            {'label': s, 'value': int(v), 'formatted': str(v)}
            for s, v in sc.items()
        ])

    separador()

    # ---------- Backlog por Categoria ----------
    painel_title('Backlog por <b>Categoria</b>')
    cc = df_aberto['categoria'].value_counts().head(10)

    if not cc.empty:
        hbar_list([
            {'label': c, 'value': int(v), 'formatted': str(v)}
            for c, v in cc.items()
        ])

    separador()

    # ---------- Backlog por Responsável ----------
    painel_title('Backlog por <b>Responsável</b>')
    resp_ab = df_aberto[
        df_aberto['responsavel_atual'].notna() &
        (df_aberto['responsavel_atual'] != 'Não informado')
    ]['responsavel_atual'].value_counts().head(10)

    if not resp_ab.empty:
        hbar_list([
            {'label': r,
             'value': int(v),
             'formatted': str(v),
             'accent': v >= 10}
            for r, v in resp_ab.items()
        ])

    separador()

    # ---------- Aging por Faixa ----------
    painel_title('Aging por <b>Faixa</b>')

    bins = pd.cut(
        df_aberto['dias_aberto'],
        bins=[-1, 5, 10, 15, 20, 30, 9999],
        labels=['0-5d', '6-10d', '11-15d', '16-20d', '21-30d', '30d+'],
    )
    dist = bins.value_counts().sort_index().reset_index()
    dist.columns = ['faixa', 'qtd']

    if not dist.empty:
        hbar_list([
            {'label': r['faixa'],
             'value': int(r['qtd']),
             'formatted': str(int(r['qtd'])),
             'accent': r['faixa'] in ['21-30d', '30d+']}
            for _, r in dist.iterrows()
        ])

    separador()

    # ---------- Top 20 mais antigos ----------
    painel_title('Tickets Mais <b>Antigos em Aberto</b>')
    antigos = df_aberto.nlargest(20, 'dias_aberto')[
        ['id', 'titulo', 'status', 'responsavel_atual', 'prioridade', 'dias_aberto']
    ].copy()
    antigos.columns = ['ID', 'Título', 'Status', 'Responsável', 'Prioridade', 'Dias']

    st.dataframe(
        antigos,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Dias': st.column_config.NumberColumn('Dias', format='%dd'),
        },
    )

    # ---------- Insights ----------
    if antigos_30 > 0:
        callout(
            'warning', 'Atenção',
            f'<b>{antigos_30} tickets</b> estão em aberto há mais de 30 dias. '
            f'Priorize os mais antigos.'
        )

    if aging > 15:
        callout(
            'warning', 'Atenção',
            f'Aging médio em <b>{aging:.0f} dias</b> — acima do ideal (15 dias).'
        )
    elif aging > 8:
        callout(
            'info', 'Insight',
            f'Aging médio em <b>{aging:.0f} dias</b> — dentro do aceitável.'
        )
    else:
        callout(
            'success', 'OK',
            f'Aging médio em <b>{aging:.0f} dias</b> — excelente.'
        )

    # Top ofensor
    if not resp_ab.empty:
        top_resp, top_qtd = resp_ab.index[0], resp_ab.iloc[0]
        if top_qtd >= 15:
            callout(
                'warning', 'Atenção',
                f'<b>{top_resp}</b> tem <b>{top_qtd} tickets em aberto</b>. '
                f'Considere redistribuir a carga.'
            )