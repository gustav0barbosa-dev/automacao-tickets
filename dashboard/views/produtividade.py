# ============================================================
# dashboard/pages/produtividade.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
)
from config import COR_BAR, COR_DANGER, COR_TEXT_SEC


def render(df):
    page_header('Produtividade por', 'Responsável',
                'Análise de volume e tempo por analista.')

    # ---------- Filtra responsáveis válidos ----------
    df_resp = df[
        df['responsavel_atual'].notna() &
        (df['responsavel_atual'] != '') &
        (df['responsavel_atual'] != 'Não informado')
    ].copy()

    if df_resp.empty:
        callout('warning', 'Atenção', 'Sem responsáveis identificados no período.')
        return

    # ---------- Agrega por responsável ----------
    agg = df_resp.groupby('responsavel_atual').agg(
        total=('id', 'count'),
        resolvidos=('status', lambda x: x.isin(['Resolvido', 'Fechado']).sum()),
        em_aberto=('status', lambda x: (
            ~x.isin(['Resolvido', 'Fechado', 'Cancelado', 'Duplicado'])
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
        kpi('Analistas Ativos', f'{len(agg)}')
    with col2:
        kpi('Total de Tickets', f'{agg["Total"].sum()}')
    with col3:
        kpi('Média por Analista', f'{agg["Total"].mean():.0f}',
            pill='tickets')

    separador()

    # ---------- Ranking por Volume ----------
    painel_title('Ranking por <b>Volume</b>')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Barras vermelhas = tempo médio acima de 9 dias</div>',
        unsafe_allow_html=True,
    )

    hbar_list([
        {'label': r['Responsável'],
         'value': int(r['Total']),
         'formatted': str(int(r['Total'])),
         'accent': pd.notna(r['Dias Médio']) and r['Dias Médio'] > 9}
        for _, r in agg.iterrows()
    ])

    separador()

    # ---------- Volume vs Tempo ----------
    painel_title('Volume vs. <b>Tempo Médio</b>')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Tamanho do ponto = tickets em aberto · Vermelho = acima de 9 dias</div>',
        unsafe_allow_html=True,
    )

    agg_plot = agg.dropna(subset=['Dias Médio'])
    if not agg_plot.empty:
        # Cria o gráfico com Plotly Graph Objects para customização
        import plotly.graph_objects as go

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

    separador()

    # ---------- Tabela detalhada ----------
    painel_title('Tabela <b>Detalhada</b>')
    st.dataframe(
        agg,
        use_container_width=True,
        hide_index=True,
        column_config={
            '% Resolução': st.column_config.ProgressColumn(
                '% Resolução',
                help='% de tickets resolvidos/fechados',
                min_value=0,
                max_value=100,
                format='%.1f%%',
            ),
        },
    )

    separador()

    # ---------- Alertas de sobrecarga ----------
    st.markdown('### ⚠️ Alertas de Sobrecarga')

    algum_alerta = False
    for _, r in agg.iterrows():
        if r['Em Aberto'] >= 10:
            callout(
                'warning', 'Atenção',
                f'<b>{r["Responsável"]}</b> tem '
                f'<b>{int(r["Em Aberto"])} tickets em aberto</b>.'
            )
            algum_alerta = True
        elif pd.notna(r['Dias Médio']) and r['Dias Médio'] > 9:
            callout(
                'warning', 'Atenção',
                f'<b>{r["Responsável"]}</b> tem tempo médio de '
                f'<b>{r["Dias Médio"]:.1f} dias</b> — acima do ideal (>9d).'
            )
            algum_alerta = True

    if not algum_alerta:
        callout('success', 'OK', 'Nenhum alerta de sobrecarga identificado.')