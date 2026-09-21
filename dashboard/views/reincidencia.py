# ============================================================
# dashboard/pages/reincidencia.py
# ============================================================

import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
    botao_exportar, legenda_grafico, info_grafico,
)
from config import COR_GOLD

# ============================================================
# Funções auxiliares
# ============================================================
def calcular_reincidencia_por_solicitante(df_sol):
    """Agrega por solicitante."""
    agg = df_sol.groupby('solicitante').agg(
        total=('id', 'count'),
        primeiro=('criado_data', 'min'),
        ultimo=('criado_data', 'max'),
        categorias=('categoria', lambda x: x.nunique()),
    ).reset_index()
    agg.columns = ['Solicitante', 'Total', 'Primeiro', 'Último', 'Categorias']
    return agg


def calcular_tempo_entre_reincidencias(df_sol):
    """Calcula tempo médio entre tickets do mesmo solicitante."""
    df = df_sol.sort_values(['solicitante', 'criado_data']).copy()
    df['ticket_anterior'] = df.groupby('solicitante')['criado_data'].shift(1)
    df['dias_entre'] = (df['criado_data'] - df['ticket_anterior']).dt.days

    # Só tickets que TEM anterior
    df_rein = df.dropna(subset=['dias_entre']).copy()

    return df_rein

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


    # ==================== TEMPO ENTRE REINCIDÊNCIAS ====================
    painel_title('Tempo entre <b>Reincidências</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Quanto tempo leva até o mesmo solicitante abrir outro ticket'
                '</div>',
                unsafe_allow_html=True)

    df_rein = calcular_tempo_entre_reincidencias(df_sol)

    if not df_rein.empty:
        col_a, col_b = st.columns(2)

        with col_a:
            # KPIs
            media_dias = df_rein['dias_entre'].mean()
            mediana_dias = df_rein['dias_entre'].median()

            col1, col2 = st.columns(2)
            with col1:
                kpi('Tempo Médio', f'{media_dias:.0f}d')
            with col2:
                kpi('Mediana', f'{mediana_dias:.0f}d')

            # Distribuição em faixas
            st.markdown('**Distribuição**')
            bins = pd.cut(
                df_rein['dias_entre'],
                bins=[-1, 7, 30, 90, 180, 9999],
                labels=['< 7d', '7-30d', '30-90d', '90-180d', '180d+']
            )
            dist = bins.value_counts().sort_index().reset_index()
            dist.columns = ['faixa', 'qtd']

            hbar_list([
                {'label': r['faixa'],
                 'value': int(r['qtd']),
                 'formatted': str(int(r['qtd'])),
                 'accent': r['faixa'] in ['< 7d', '7-30d']}
                for _, r in dist.iterrows()
            ])

        with col_b:
            # Top 10 solicitantes que mais rápido voltam
            st.markdown('**Quem volta mais rápido**')

            rapido = df_rein.groupby('solicitante').agg(
                media_dias=('dias_entre', 'mean'),
                qtd=('dias_entre', 'count'),
            ).reset_index()
            rapido = rapido[rapido['qtd'] >= 2].sort_values('media_dias').head(10)

            if not rapido.empty:
                hbar_list([
                    {'label': r['solicitante'][:25],
                     'value': float(r['media_dias']),
                     'formatted': f'{r["media_dias"]:.0f}d ({int(r["qtd"])}x)',
                     'accent': r['media_dias'] < 7}
                    for _, r in rapido.iterrows()
                ])
            else:
                callout('info', 'Info', 'Sem dados suficientes.')

        # Insight
        if mediana_dias < 15:
            callout('warning', 'Atenção',
                    f'Mediana de <b>{mediana_dias:.0f} dias</b> entre reincidências '
                    f'é baixa — problemas voltando rápido.')
        else:
            callout('info', 'Insight',
                    f'Mediana de <b>{mediana_dias:.0f} dias</b> entre reincidências.')

    separador()

    # ==================== REINCIDÊNCIA POR CATEGORIA ====================
    painel_title('Reincidência por <b>Categoria</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Categorias com maior taxa de reincidência'
                '</div>',
                unsafe_allow_html=True)

    # Por categoria: conta tickets totais e solicitantes únicos
    cat_agg = df_sol.groupby('categoria').agg(
        tickets=('id', 'count'),
        solicitantes=('solicitante', 'nunique'),
    ).reset_index()
    cat_agg['taxa_rein'] = (cat_agg['tickets'] / cat_agg['solicitantes']).round(2)
    cat_agg = cat_agg[cat_agg['solicitantes'] >= 3]
    cat_agg = cat_agg.sort_values('taxa_rein', ascending=False).head(10)

    if not cat_agg.empty:
        hbar_list([
            {'label': r['categoria'][:25],
             'value': float(r['taxa_rein']),
             'formatted': f'{r["taxa_rein"]:.1f} ticket/sol.',
             'accent': r['taxa_rein'] > 3}
            for _, r in cat_agg.iterrows()
        ])

        pior = cat_agg.iloc[0]
        if pior['taxa_rein'] > 3:
            callout('warning', 'Atenção',
                    f'Categoria <b>{pior["categoria"]}</b> tem '
                    f'<b>{pior["taxa_rein"]:.1f} tickets por solicitante</b> — '
                    f'indicador de problema sistêmico.')

    separador()

    # ==================== REINCIDÊNCIA POR EMPRESA ====================
    painel_title('Reincidência por <b>Empresa do Responsável</b>')

    if 'responsavel_empresa' in df_sol.columns:
        emp_agg = df_sol.groupby('responsavel_empresa').agg(
            tickets=('id', 'count'),
            solicitantes=('solicitante', 'nunique'),
        ).reset_index()
        emp_agg['taxa'] = (emp_agg['tickets'] / emp_agg['solicitantes']).round(2)
        emp_agg = emp_agg.sort_values('taxa', ascending=False)

        hbar_list([
            {'label': r['responsavel_empresa'],
             'value': float(r['taxa']),
             'formatted': f'{r["taxa"]:.2f} ticket/sol.',
             'accent': r['taxa'] > 3}
            for _, r in emp_agg.iterrows()
        ])

    separador()

    # ==================== REINCIDÊNCIA POR MÊS ====================
    painel_title('Evolução da <b>Reincidência</b> por Mês')

    df_mes = df_sol.copy()
    df_mes['mes'] = df_mes['criado_data'].dt.to_period('M').astype(str)

    mes_agg = df_mes.groupby('mes').agg(
        tickets=('id', 'count'),
        solicitantes=('solicitante', 'nunique'),
    ).reset_index()
    mes_agg['taxa'] = (mes_agg['tickets'] / mes_agg['solicitantes']).round(2)
    mes_agg = mes_agg.sort_values('mes').tail(12)

    if not mes_agg.empty:


        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=mes_agg['mes'],
            y=mes_agg['taxa'],
            mode='lines+markers',
            line=dict(color=COR_GOLD, width=2),
            marker=dict(color=COR_GOLD, size=8),
            fill='tozeroy',
            fillcolor='rgba(201,166,102,.15)',
        ))
        fig.update_layout(
            height=300,
            xaxis_title='',
            yaxis_title='Tickets por solicitante',
            xaxis_tickangle=-45,
        )
        fig = aplicar_tema_plotly(fig, altura=300)
        st.plotly_chart(fig, use_container_width=True,
                        config={'displayModeBar': False})

        legenda_grafico([
            {'cor': COR_GOLD, 'label': 'Tickets por solicitante', 'tipo': 'linha'},
        ])
        info_grafico(
            'Valores acima de 1 indicam que, em média, o mesmo solicitante '
            'abriu mais de um ticket naquele mês.'
        )

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