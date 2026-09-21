# ============================================================
# dashboard/views/diagnostico.py
# ============================================================

import pandas as pd
import plotly.express as px
import streamlit as st

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
    botao_exportar, legenda_grafico, info_grafico,
)
from config import COR_SUCCESS, COR_DANGER, COR_WARNING, STATUS_FECHADOS


# Descrição dos cenários da matriz de verdade
DESCRICAO_CENARIOS = {
    'CEN-01': 'SPPREV resp × SPPREV alt × Aguardando',
    'CEN-02': 'SPPREV resp × Atlantic alt × Aguardando',
    'CEN-03': 'SPPREV resp × SPPREV alt × Em atendimento',
    'CEN-04': 'SPPREV resp × Atlantic alt × Em atendimento',
    'CEN-05': 'SPPREV resp × SPPREV alt × Resolvido',
    'CEN-06': 'SPPREV resp × Atlantic alt × Resolvido',
    'CEN-07': 'Atlantic resp × SPPREV alt × Aguardando',
    'CEN-08': 'Atlantic resp × Atlantic alt × Aguardando',
    'CEN-09': 'Atlantic resp × SPPREV alt × Em atendimento',
    'CEN-10': 'Atlantic resp × Atlantic alt × Em atendimento',
    'CEN-11': 'Atlantic resp × SPPREV alt × Resolvido',
    'CEN-12': 'Atlantic resp × Atlantic alt × Resolvido',
    'OUTRO':  'Não classificado',
}


def render(df):
    page_header('Diagnóstico', 'de Tickets',
                'Análise da matriz de verdade, gargalos e tickets travados.')

    # ==================== DADOS BASE ====================
    df_diag = df[df['diagnostico'].notna()].copy()

    if df_diag.empty:
        callout('warning', 'Atenção',
                'Sem tickets diagnosticados. Rode `python scripts/diagnosticar_tickets.py`.')
        return

    # ==================== KPIs PRINCIPAIS ====================
    total = len(df)
    com_diag = len(df_diag)  # inclui CEN-XX + OUTRO + SEM_DADOS
    com_diag_real = len(df_diag[~df_diag['diagnostico'].isin(['OUTRO', 'SEM_DADOS'])])
    sem_diag = total - com_diag

    # Tickets em aberto (diagnóstico)
    df_aberto = df_diag[~df_diag['status'].isin(STATUS_FECHADOS)]

    # Backlog
    em_backlog = len(df_aberto[df_aberto['backlog'] == 1]) if 'backlog' in df_aberto.columns else 0

    # Abertos ativos = em aberto, fora do backlog, COM diagnóstico real (exclui SEM_DADOS e OUTRO)
    df_aberto_ativos = df_aberto[
        (df_aberto.get('backlog', 0) == 0) &
        (~df_aberto['diagnostico'].isin(['OUTRO', 'SEM_DADOS']))
    ].copy()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Tickets no Filtro', f'{total}')
    with col2:
        kpi('Diagnosticados (CEN-XX)', f'{com_diag_real}',
            pill=f'{com_diag_real/total*100:.1f}%' if total else '—',
            pill_tipo='positive' if com_diag_real > 0 else 'neutral',
            ajuda=f'{com_diag} com algum dado, {sem_diag} sem movimentação')
    with col3:
        kpi('Em Backlog', f'{em_backlog}',
            pill='Suprimido',
            pill_tipo='neutral',
            ajuda='Tickets na fila do backlog — não geram alerta')
    with col4:
        kpi('Abertos Ativos', f'{len(df_aberto_ativos)}',
            pill='⚠️ Analisar' if len(df_aberto_ativos) > 0 else 'OK',
            pill_tipo='negative' if len(df_aberto_ativos) > 0 else 'positive',
            ajuda='Tickets em aberto, fora do backlog, com cenário definido')

    separador()

    # ==================== DIAGNÓSTICO: AÇÃO INTERNA vs EXTERNA ====================
    painel_title('Ação Interna vs <b>Externa</b>')

    df_ab = df_aberto_ativos.copy()
    n_acao_interna = (df_ab['acao_interna'] == 1).sum()
    n_acao_externa = (df_ab['acao_interna'] == 0).sum()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                    'Tickets em aberto (fora do backlog)</div>',
                    unsafe_allow_html=True)
        hbar_list([
            {'label': '✅ Resp. = Alterador', 'value': int(n_acao_interna),
             'formatted': f'{n_acao_interna} ({n_acao_interna/max(len(df_ab),1)*100:.0f}%)'},
            {'label': '⚠️ Resp. ≠ Alterador', 'value': int(n_acao_externa),
             'formatted': f'{n_acao_externa} ({n_acao_externa/max(len(df_ab),1)*100:.0f}%)',
             'accent': True},
        ])

    with col_b:
        # Pizza
        fig = px.pie(
            values=[n_acao_interna, n_acao_externa],
            names=['Resp. = Alterador', 'Resp. ≠ Alterador'],
            hole=0.4,
            color_discrete_map={
                'Resp. = Alterador': COR_SUCCESS,
                'Resp. ≠ Alterador': COR_DANGER,
            },
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            height=260,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#eae7e1'),
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        legenda_grafico([
            {'cor': COR_SUCCESS, 'label': 'Responsável = Alterador'},
            {'cor': COR_DANGER, 'label': 'Responsável ≠ Alterador'},
        ])
        info_grafico(
            '<b>Resp. = Alterador</b>: o responsável fez a última ação. '
            '<b>Resp. ≠ Alterador</b>: outra pessoa mexeu (pode indicar '
            'backlog ou encaminhamento).'
        )

    separador()

    # ==================== TICKETS TRAVADOS ====================
    st.markdown('### 🚨 Tickets Travados')

    callout('info', 'Definição',
            'Tickets em aberto <b>de responsabilidade SPPREV</b>, com '
            '<b>Resp. = Alterador</b>, fora do backlog, com mais de 3 dias sem ação. '
            'Tickets com responsável <b>Atlantic</b> não geram alerta (não competem ao SPPREV).')

    # Filtro: só SPPREV
    df_spprev = df_aberto_ativos[
        df_aberto_ativos['responsavel_empresa'] == 'SPPREV'
    ].copy()

    # Filtro: travados
    df_travados = df_spprev[
        (df_spprev['acao_interna'] == 1) &
        (df_spprev['dias_aberto'] > 3)
    ].copy()

    # Tickets Atlantic "travados" — apenas informativo
    df_atlantic_info = df_aberto_ativos[
        (df_aberto_ativos['responsavel_empresa'] == 'Atlantic') &
        (df_aberto_ativos['acao_interna'] == 1) &
        (df_aberto_ativos['dias_aberto'] > 3)
    ].copy()

    if df_travados.empty:
        callout('success', 'OK',
                f'Nenhum ticket travado SPPREV. '
                f'({len(df_atlantic_info)} tickets Atlantic em situação similar — '
                f'não geram alerta)')
    else:
        # KPIs dos travados
        col1, col2, col3 = st.columns(3)
        with col1:
            kpi('Tickets Travados SPPREV', f'{len(df_travados)}',
                pill='⚠️ Atenção', pill_tipo='negative')
        with col2:
            aging = df_travados['dias_aberto'].mean()
            kpi('Aging Médio', f'{aging:.0f}d')
        with col3:
            mais_antigo = df_travados['dias_aberto'].max()
            kpi('Mais Antigo', f'{mais_antigo:.0f}d')

        st.markdown('')

        # Top responsáveis
        painel_title('Travados por <b>Responsável (SPPREV)</b>')
        top_resp = df_travados['responsavel_atual'].value_counts().head(10)
        hbar_list([
            {'label': r[:25],
             'value': int(v),
             'formatted': str(v),
             'accent': v >= 3}
            for r, v in top_resp.items()
        ])

        st.markdown('')

        # Tabela detalhada
        painel_title('Lista <b>Detalhada</b> — SPPREV')
        tabela = df_travados.nlargest(30, 'dias_aberto')[
            ['id', 'titulo', 'status', 'responsavel_atual', 'dias_aberto']
        ].copy()
        tabela.columns = ['ID', 'Título', 'Status', 'Responsável', 'Dias Aberto']
        tabela['Título'] = tabela['Título'].str.slice(0, 50)

        st.dataframe(
            tabela,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Dias Aberto': st.column_config.NumberColumn(
                    'Dias Aberto', format='%dd'
                ),
            },
        )

    # ==================== INFO: Atlantic em situação similar ====================
    if not df_atlantic_info.empty:
        st.markdown('')
        painel_title('ℹ️ Tickets <b>Atlantic</b> em situação similar (não alertam)')
        st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                    'Responsável Atlantic com Resp.=Alterador — fora da competência SPPREV'
                    '</div>',
                    unsafe_allow_html=True)

        col_info1, col_info2 = st.columns(2)
        with col_info1:
            kpi('Total', f'{len(df_atlantic_info)}',
                pill='Informativo', pill_tipo='neutral')
        with col_info2:
            aging_atl = df_atlantic_info['dias_aberto'].mean()
            kpi('Aging Médio', f'{aging_atl:.0f}d')

        with st.expander('Ver lista'):
            tabela_atl = df_atlantic_info.nlargest(20, 'dias_aberto')[
                ['id', 'titulo', 'status', 'responsavel_atual', 'dias_aberto']
            ].copy()
            tabela_atl.columns = ['ID', 'Título', 'Status', 'Responsável', 'Dias Aberto']
            tabela_atl['Título'] = tabela_atl['Título'].str.slice(0, 50)
            st.dataframe(tabela_atl, use_container_width=True, hide_index=True)

    separador()

    # ==================== MATRIZ DOS 12 CENÁRIOS ====================
    # ==================== MATRIZ DOS 12 CENÁRIOS ====================
    painel_title('Distribuição dos <b>12 Cenários</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Matriz de verdade: Cruzamento de responsável × alterador × status'
                '</div>',
                unsafe_allow_html=True)

    # Conta cenários
    dist = df_diag['diagnostico'].value_counts().reset_index()
    dist.columns = ['cenario', 'qtd']
    dist = dist.sort_values('cenario')

    # Separa em 3 grupos
    dist_12 = dist[~dist['cenario'].isin(['OUTRO', 'SEM_DADOS'])]
    dist_outro = dist[dist['cenario'] == 'OUTRO']
    dist_sem = dist[dist['cenario'] == 'SEM_DADOS']

    # --- 12 cenários ---
    if not dist_12.empty:
        hbar_list([
            {'label': f'{r["cenario"]} — {DESCRICAO_CENARIOS.get(r["cenario"], "")[:40]}',
             'value': int(r['qtd']),
             'formatted': str(int(r['qtd'])),
             'accent': r['cenario'] in ['CEN-02', 'CEN-04', 'CEN-06',
                                        'CEN-07', 'CEN-09', 'CEN-11']}
            for _, r in dist_12.iterrows()
        ])

    # --- OUTROS ---
    if not dist_outro.empty:
        qtd_outro = int(dist_outro['qtd'].iloc[0])
        st.markdown(f'''
            <div style="margin-top:20px; padding:12px 16px;
                        background:#1b2029; border:1px solid rgba(255,255,255,.07);
                        border-left:3px solid #d9ac53; border-radius:6px;">
                <div style="font-size:11px; color:#d9ac53; text-transform:uppercase;
                            letter-spacing:.5px; font-weight:700; margin-bottom:4px;">
                    ⚠️ Fora da Matriz
                </div>
                <div style="color:#9299a6; font-size:13px;">
                    <b style="color:#eae7e1;">{qtd_outro}</b> tickets com movimentação,
                    mas status fora dos 3 mapeados
                    (<span style="color:#c9a666;">Aguardando</span>,
                     <span style="color:#c9a666;">Em atendimento</span>,
                     <span style="color:#c9a666;">Resolvido</span>).
                    Provavelmente são tickets já <b>Fechados</b> ou <b>Cancelados</b>.
                </div>
            </div>
        ''', unsafe_allow_html=True)

    # --- SEM DADOS ---
    if not dist_sem.empty:
        qtd_sem = int(dist_sem['qtd'].iloc[0])
        st.markdown(f'''
            <div style="margin-top:12px; padding:12px 16px;
                        background:#1b2029; border:1px solid rgba(255,255,255,.07);
                        border-left:3px solid #5c6270; border-radius:6px;">
                <div style="font-size:11px; color:#5c6270; text-transform:uppercase;
                            letter-spacing:.5px; font-weight:700; margin-bottom:4px;">
                    📊 Sem Dados
                </div>
                <div style="color:#9299a6; font-size:13px;">
                    <b style="color:#eae7e1;">{qtd_sem}</b> tickets ainda não foram
                    enriquecidos (sem movimentação capturada).
                    Rode o Programa5 para melhorar a cobertura.
                </div>
            </div>
        ''', unsafe_allow_html=True)

    separador()

    # ==================== TABELA CRUZADA POR STATUS ====================
    painel_title('Tabela <b>Cruzada</b> por Status')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Cenários por status do ticket</div>',
                unsafe_allow_html=True)

    # Pivot
    df_cruz = df_diag[~df_diag['diagnostico'].isin(['OUTRO', 'SEM_DADOS'])].copy()
    if not df_cruz.empty:
        cruz = df_cruz.groupby(['status', 'diagnostico']).size().reset_index(name='qtd')
        pivot = cruz.pivot(index='status', columns='diagnostico', values='qtd').fillna(0).astype(int)
        st.dataframe(pivot, use_container_width=True)
    else:
        callout('info', 'Info', 'Sem dados para tabela cruzada.')

    separador()

    # ==================== INSIGHTS ====================
    st.markdown('### 💡 Insights')

    if len(df_travados) > 0:
        pior = df_travados['responsavel_atual'].value_counts().index[0]
        callout('warning', 'Atenção',
                f'<b>{len(df_travados)} tickets travados</b> em aberto. '
                f'Responsável com mais casos: <b>{pior}</b>.')
    else:
        callout('success', 'OK', 'Nenhum ticket travado identificado.')

    if em_backlog > 0:
        callout('info', 'Info',
                f'<b>{em_backlog} tickets</b> estão em backlog e foram '
                f'considerados "saudáveis" — não geram alerta.')

    if com_diag < total * 0.5:
        callout('warning', 'Atenção',
                f'Apenas <b>{com_diag} de {total}</b> tickets foram '
                f'diagnosticados. Rode o Programa5 em mais dias para melhorar a cobertura.')

    separador()
    
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df_diag, 'diagnostico', key='export_diagnostico')