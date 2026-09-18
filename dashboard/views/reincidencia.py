# ============================================================
# dashboard/pages/reincidencia.py
# ============================================================

import streamlit as st
import pandas as pd

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title,
    botao_exportar,
)


def render(df):
    page_header('Reincidência', '',
                'Análise de solicitantes que abrem múltiplos tickets.')

    # ---------- Filtra solicitantes válidos ----------
    df_sol = df[
        df['solicitante'].notna() &
        (df['solicitante'] != '') &
        (df['solicitante'] != 'Não informado')
    ].copy()

    if df_sol.empty:
        callout('warning', 'Atenção', 'Sem solicitantes identificados no período.')
        return

    # ---------- Agrega por solicitante ----------
    agg = df_sol.groupby('solicitante').agg(
        total=('id', 'count'),
        primeiro=('criado_data', 'min'),
        ultimo=('criado_data', 'max'),
        categorias=('categoria', lambda x: x.nunique()),
    ).reset_index()
    agg.columns = ['Solicitante', 'Total', 'Primeiro', 'Último', 'Categorias']

    # ---------- KPIs ----------
    total_solicitantes = len(agg)
    reincidentes = len(agg[agg['Total'] >= 2])
    muito_reincidentes = len(agg[agg['Total'] >= 5])
    taxa = (reincidentes / total_solicitantes * 100) if total_solicitantes else 0
    media = agg['Total'].mean()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Solicitantes Únicos', f'{total_solicitantes}')
    with col2:
        kpi('Taxa de Reincidência', f'{taxa:.0f}%',
            pill=f'{reincidentes} com 2+ tickets',
            pill_tipo='negative' if taxa > 30 else 'neutral')
    with col3:
        kpi('Média Tickets/Solicitante', f'{media:.1f}')
    with col4:
        kpi('Alta Reincidência (5+)', f'{muito_reincidentes}',
            pill='Atenção' if muito_reincidentes > 0 else 'OK',
            pill_tipo='negative' if muito_reincidentes > 0 else 'positive')

    separador()

    # ---------- Distribuição + Top 10 ----------
    col_a, col_b = st.columns(2)

    with col_a:
        painel_title('Tickets por <b>Solicitante</b>')

        dist = agg['Total'].value_counts().sort_index().reset_index()
        dist.columns = ['qtd', 'solicitantes']

        dist_final = dist[dist['qtd'] <= 4].copy()
        qtd_5mais = dist[dist['qtd'] >= 5]['solicitantes'].sum()
        if qtd_5mais > 0:
            dist_final = pd.concat([
                dist_final,
                pd.DataFrame([{'qtd': '5+', 'solicitantes': qtd_5mais}])
            ])

        hbar_list([
            {'label': str(r['qtd']) + (' ticket' if r['qtd'] == 1 else ' tickets'),
             'value': int(r['solicitantes']),
             'formatted': str(int(r['solicitantes'])),
             'accent': str(r['qtd']) == '5+'}
            for _, r in dist_final.iterrows()
        ])

    with col_b:
        painel_title('Top 10 <b>Reincidentes</b>')
        top = agg.nlargest(10, 'Total').sort_values('Total')

        hbar_list([
            {'label': r['Solicitante'][:22],
             'value': int(r['Total']),
             'formatted': str(int(r['Total'])),
             'accent': r['Total'] >= 5}
            for _, r in top.iterrows()
        ])

    separador()

    # ---------- Reincidência por categoria ----------
    painel_title('Reincidência por <b>Categoria</b>')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Categorias com mais solicitantes reincidentes</div>',
        unsafe_allow_html=True,
    )

    df_sol_rein = df_sol[df_sol['solicitante'].isin(
        agg[agg['Total'] >= 2]['Solicitante']
    )].copy()

    if not df_sol_rein.empty:
        cat_rein = df_sol_rein.groupby('categoria').agg(
            tickets=('id', 'count'),
            solicitantes=('solicitante', 'nunique'),
        ).reset_index()
        cat_rein['media_por_solicitante'] = (
            cat_rein['tickets'] / cat_rein['solicitantes']
        ).round(1)
        cat_rein = cat_rein[cat_rein['solicitantes'] >= 2]
        cat_rein = cat_rein.sort_values('tickets', ascending=False).head(10)

        if not cat_rein.empty:
            hbar_list([
                {'label': r['categoria'],
                 'value': int(r['tickets']),
                 'formatted': f'{int(r["tickets"])} ({r["media_por_solicitante"]:.1f}/sol.)',
                 'accent': r['media_por_solicitante'] > 3}
                for _, r in cat_rein.iterrows()
            ])
        else:
            callout('info', 'Info',
                    'Sem categorias com 2+ solicitantes reincidentes.')
    else:
        callout('info', 'Info', 'Sem dados de reincidência por categoria.')

    separador()

    # ---------- Tabela detalhada ----------
    painel_title('Detalhamento — Solicitantes com <b>3+ tickets</b>')

    tabela = agg[agg['Total'] >= 3].copy()
    tabela = tabela.sort_values('Total', ascending=False).head(30)

    if not tabela.empty:
        # Formata datas
        tabela['Primeiro'] = pd.to_datetime(tabela['Primeiro']).dt.strftime('%d/%m/%Y')
        tabela['Último'] = pd.to_datetime(tabela['Último']).dt.strftime('%d/%m/%Y')

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Total': st.column_config.NumberColumn('Tickets', format='%d'),
                'Categorias': st.column_config.NumberColumn('Categorias', format='%d'),
            },
        )
    else:
        callout('success', 'OK', 'Nenhum solicitante com 3+ tickets.')

    separador()

    # ---------- Insights ----------
    st.markdown('### 💡 Insights')

    if taxa > 40:
        callout(
            'warning', 'Atenção',
            f'Taxa de reincidência em <b>{taxa:.0f}%</b> — '
            f'mais de 4 em cada 10 solicitantes abrem mais de um ticket. '
            f'Isso indica <b>problema sistêmico</b>, não pontual.'
        )
    elif taxa > 20:
        callout(
            'info', 'Insight',
            f'Taxa de reincidência em <b>{taxa:.0f}%</b> — '
            f'valor dentro do esperado para operações complexas.'
        )
    else:
        callout(
            'success', 'OK',
            f'Taxa de reincidência em <b>{taxa:.0f}%</b> — '
            f'excelente! Problemas pontuais sendo resolvidos na primeira.'
        )

    # Top reincidente
    if not agg.empty:
        top1 = agg.nlargest(1, 'Total').iloc[0]
        if top1['Total'] >= 5:
            callout(
                'warning', 'Atenção',
                f'<b>{top1["Solicitante"]}</b> abriu '
                f'<b>{int(top1["Total"])} tickets</b> '
                f'em {int(top1["Categorias"])} categoria(s) — analisar caso a caso.'
            )

    separador()
    
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(agg, 'reincidencia', key='export_reincidencia')