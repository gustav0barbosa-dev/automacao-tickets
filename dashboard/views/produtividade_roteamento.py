# ============================================================
# dashboard/views/produtividade_roteamento.py — Produtividade + Roteamento
# ============================================================
"""
Página unificada de Produtividade e Roteamento (Fase 3 — Etapa 3).

Combina:
  - Produtividade: tempo por responsável/área, volume, SLA por responsável
  - Roteamento: grafo de encaminhamentos, linha do tempo por ticket
"""

import io
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.productivity_service import (
    calcular_produtividade_por_responsavel,
    calcular_tempo_por_responsavel,
)
from services.routing_service import (
    calcular_fluxo_roteamento,
    calcular_tempo_por_responsavel as calc_tempo_por_resp_alt,
    calcular_gaps_movimentacao,
)
from components import (
    kpi, callout, separador, hbar_list, painel_title,
    aplicar_tema_plotly, botao_exportar, legenda_grafico,
    info_grafico, chart_card, card_com_tabela, card_com_barras,
    global_header, empty_state, insight_card,
)
from lucide import lucide
from config import COR_BAR, COR_DANGER, COR_TEXT_SEC
from data import carregar_movimentacoes, carregar_mensagens, carregar_analistas


def render(df_filtrado: pd.DataFrame):
    st.title('📊 Produtividade + Roteamento')
    st.markdown(
        'Análise do ciclo de vida do ticket: quanto tempo aguarda, quanto tempo '
        'permanece com cada responsável ou área, quantas transferências ocorrem '
        'e qual caminho percorre até a resolução.'
    )

    # ==================== CARREGA DADOS AUXILIARES ====================
    df_movs = carregar_movimentacoes()
    df_msgs = carregar_mensagens()
    df_analistas = carregar_analistas()

    if df_movs.empty:
        callout('warning', 'Atenção',
                'Sem movimentações. Execute o pipeline de enriquecimento '
                'para habilitar a análise de roteamento.')
        return

    # ==================== KPIs GERAIS ====================
    total_tickets = df_movs['ticket_id'].nunique()
    pessoas_por_ticket = df_movs.groupby('ticket_id')['autor'].nunique()
    media_pessoas = pessoas_por_ticket.mean() if not pessoas_por_ticket.empty else 0
    msgs_total = len(df_msgs)
    tickets_alto = len(pessoas_por_ticket[pessoas_por_ticket >= 5])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Tickets Enriquecidos', f'{total_tickets}')
    with col2:
        kpi('Média Pessoas/Ticket', f'{media_pessoas:.1f}',
            pill='Alto' if media_pessoas > 3.5 else 'OK',
            pill_tipo='negative' if media_pessoas > 3.5 else 'positive')
    with col3:
        kpi('Mensagens Capturadas', f'{msgs_total}')
    with col4:
        kpi('Tickets com 5+ Pessoas', f'{tickets_alto}',
            pill='Atenção' if tickets_alto > 5 else 'OK',
            pill_tipo='negative' if tickets_alto > 5 else 'positive')

    separador()

    # ==================== ABA 1: PRODUTIVIDADE ====================
    st.markdown('## 📈 Produtividade por Responsável')

    df_resp = df_filtrado.copy()
    df_resp = df_resp[
        df_resp['responsavel_atual'].notna()
        & (df_resp['responsavel_atual'] != '')
        & (df_resp['responsavel_atual'] != 'Não informado')
    ]

    if df_resp.empty:
        empty_state(
            titulo='Sem responsáveis identificados',
            descricao='Nenhum ticket tem responsável no período selecionado.',
            icone='users',
        )
    else:
        # Converte datas
        df_resp['criado_data'] = pd.to_datetime(df_resp['criado_data'], errors='coerce')
        df_resp['data_resolvido'] = pd.to_datetime(df_resp['data_resolvido'], errors='coerce')
        df_resp['dias_resolucao_calc'] = (
            df_resp['data_resolvido'] - df_resp['criado_data']
        ).dt.total_seconds() / 86400

        status_resolvidos = {'Resolvido', 'Fechado'}

        agg = (
            df_resp.groupby('responsavel_atual')
            .agg(
                total_tickets=('id', 'count'),
                resolvidos=('status', lambda x: (x.isin(status_resolvidos)).sum()),
                em_aberto=('status', lambda x: (
                    ~x.isin(status_resolvidos | {'Cancelado', 'Duplicado'})
                ).sum()),
                dias_medio_resolucao=('dias_resolucao_calc', 'mean'),
            )
            .reset_index()
        )
        agg.columns = ['Responsável', 'Total', 'Resolvidos', 'Em Aberto', 'Dias Médio']
        agg['% Resolução'] = (agg['Resolvidos'] / agg['Total'] * 100).round(1)
        agg['Dias Médio'] = agg['Dias Médio'].round(1)
        agg = agg.sort_values('Total', ascending=False)

        # KPIs
        col1, col2, col3 = st.columns(3)
        with col1:
            kpi('Analistas Ativos', f'{len(agg)}', icone='users')
        with col2:
            kpi('Total de Tickets', f'{agg["Total"].sum()}', icone='inbox')
        with col3:
            kpi('Média por Analista', f'{agg["Total"].mean():.0f}',
                pill='tickets', icone='activity')

        # Ranking por volume
        items_ranking = [
            {
                'label': r['Responsável'],
                'value': int(r['Total']),
                'formatted': str(int(r['Total'])),
                'accent': pd.notna(r['Dias Médio']) and r['Dias Médio'] > 9
            }
            for _, r in agg.iterrows()
        ]
        card_com_barras(
            titulo='Ranking por Volume',
            descricao='Barras vermelhas = tempo médio acima de 9 dias',
            icone='bar-chart',
            items=items_ranking,
        )

        # Volume vs Tempo
        agg_plot = agg.dropna(subset=['Dias Médio'])
        if not agg_plot.empty:
            with chart_card('Volume vs Tempo Médio',
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

        # Tabela detalhada
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

        # Alertas de sobrecarga
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;"'
            f'margin:24px 0 14px 0;">'
            f'<span style="color:#c9a666;">{lucide("alert-triangle", 18)}</span>'
            f'<span style="font-family:Fraunces,serif;font-size:18px;font-weight:600;">'
            f'Alertas de Sobrecarga</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        col_a1, col_a2, col_a3 = st.columns(3)
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
            insight_card(
                'info',
                'Total Analistas',
                f'{len(agg)}',
                'ativos no período',
            )

    separador()

    # ==================== ABA 2: ROTEAMENTO ====================
    st.markdown('## 🔀 Roteamento de Tickets')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Fluxo de encaminhamentos entre analistas e identificação de gargalos.'
        '</div>',
        unsafe_allow_html=True,
    )

    df_movs_ok = df_movs.dropna(subset=['autor']).copy()

    # KPIs de roteamento
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        kpi('Tickets Enriquecidos', f'{total_tickets}')
    with col_r2:
        kpi('Média Pessoas/Ticket', f'{media_pessoas:.1f}',
            pill='Alto' if media_pessoas > 3.5 else 'OK',
            pill_tipo='negative' if media_pessoas > 3.5 else 'positive')
    with col_r3:
        kpi('Mensagens Capturadas', f'{msgs_total}')
    with col_r4:
        kpi('Tickets com 5+ Pessoas', f'{tickets_alto}',
            pill='Atenção' if tickets_alto > 5 else 'OK',
            pill_tipo='negative' if tickets_alto > 5 else 'positive')

    # Distribuição de pessoas por ticket
    col_a, col_b = st.columns(2)
    with col_a:
        painel_title('Quantas pessoas tocam <b>cada ticket</b>')
        dist = pessoas_por_ticket.value_counts().sort_index().reset_index()
        dist.columns = ['pessoas', 'qtd']
        hbar_list([
            {'label': f'{int(r["pessoas"])} pessoa(s)',
             'value': int(r['qtd']),
             'formatted': str(int(r['qtd'])),
             'accent': r['pessoas'] >= 5}
            for _, r in dist.iterrows()
        ])

    with col_b:
        painel_title('Top <b>Quem Mais Movimenta</b>')
        top_mov = df_movs_ok.groupby('autor').size()\
            .sort_values(ascending=False).head(10).reset_index()
        top_mov.columns = ['autor', 'qtd']
        hbar_list([
            {'label': r['autor'][:25],
             'value': int(r['qtd']),
             'formatted': str(int(r['qtd'])),
             'accent': 'Suporte' in r['autor']}
            for _, r in top_mov.iterrows()
        ])

    separador()

    # Gaps entre movimentações
    painel_title('Maiores <b>Gaps entre Movimentações</b>')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Onde os tickets ficaram mais tempo parados</div>',
        unsafe_allow_html=True,
    )

    df_gaps = calcular_gaps_movimentacao(df_movs_ok, limite_horas=24.0)
    if not df_gaps.empty:
        st.dataframe(
            df_gaps.head(15),
            use_container_width=True,
            hide_index=True,
            column_config={
                'dias_parado': st.column_config.NumberColumn('Dias parado', format='%.1f'),
                'data_movimentacao': st.column_config.DatetimeColumn('Data'),
                'data_anterior': st.column_config.DatetimeColumn('Data Anterior'),
            },
        )
        mediana = df_gaps['dias_parado'].median()
        grandes = len(df_gaps[df_gaps['dias_parado'] > 7])
        if mediana > 3:
            callout(
                'warning', 'Atenção',
                f'Mediana de dias entre movimentações é <b>{mediana:.1f} dias</b>. '
                f'<b>{grandes} ticket(s)</b> teve(m) gap > 7 dias.'
            )
        else:
            callout(
                'success', 'OK',
                f'Mediana de dias entre movimentações é <b>{mediana:.1f} dias</b>.'
            )
    else:
        callout('info', 'Info', 'Sem gaps relevantes (> 1 dia) identificados.')

    separador()

    # Grafo de roteamento
    painel_title('Grafo de <b>Roteamento</b>')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Fluxo de encaminhamentos entre analistas.'
        '</div>',
        unsafe_allow_html=True,
    )

    if df_analistas.empty:
        callout('info', 'Info',
                'Sem dados de analistas. Rode '
                '`python scripts/carregar_analistas.py`.')
    else:
        st.markdown('**Filtros do Grafo**')
        col_f1, col_f2, col_f3 = st.columns(3)

        hoje = date.today()
        with col_f1:
            periodo_grafo = st.date_input(
                'Período',
                value=(hoje - timedelta(days=90), hoje),
                key='grafo_periodo_prod_rot',
            )
        with col_f2:
            max_nos = st.slider(
                'Top N analistas',
                min_value=5, max_value=50, value=20, step=5,
                key='grafo_max_nos_prod_rot',
            )
        with col_f3:
            empresa_filtro = st.selectbox(
                'Empresa',
                options=['Todas', 'SPPREV', 'Atlantic', 'Externo'],
                key='grafo_empresa_prod_rot',
            )

        df_movs_filt = df_movs_ok.copy()
        if len(periodo_grafo) == 2:
            ini, fim = periodo_grafo
            df_movs_filt = df_movs_filt[
                (df_movs_filt['data_movimentacao'].dt.date >= ini) &
                (df_movs_filt['data_movimentacao'].dt.date <= fim)
            ]
        if empresa_filtro != 'Todas':
            mapa_emp = dict(zip(df_analistas['nome'], df_analistas['empresa_tipo']))
            df_movs_filt = df_movs_filt[
                df_movs_filt['autor'].map(mapa_emp) == empresa_filtro
            ]

        from components_grafo import render_legenda, render_grafo
        render_legenda()

        if df_movs_filt.empty:
            callout('info', 'Info',
                    'Sem movimentações no período/filtro selecionado.')
        else:
            st.caption(f'📊 {len(df_movs_filt)} movimentações no período')
            render_grafo(df_movs_filt, df_analistas,
                          max_nos=max_nos, altura=600)

            info_grafico(
                '<b>Tamanho do nó</b> = volume de encaminhamentos. '
                '<b>Espessura da seta</b> = quantidade. '
                '<b>Cor</b> = empresa do analista. '
                'Passe o mouse sobre os nós para ver detalhes.'
            )

    separador()

    # Árvore de um ticket individual
    painel_title('Árvore de <b>Encaminhamentos</b>')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Digite um ID de ticket para ver o fluxo completo.'
        '</div>',
        unsafe_allow_html=True,
    )

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        ticket_id = st.number_input(
            'ID do Ticket',
            min_value=1,
            value=111239,
            step=1,
            key='arvore_ticket_id_prod_rot',
            label_visibility='collapsed',
        )
    with col_btn:
        buscar = st.button('🔍 Visualizar Árvore',
                           use_container_width=True,
                           key='btn_arvore_prod_rot')

    if buscar:
        try:
            from components_grafo import render_arvore_ticket_sqlalchemy
            render_arvore_ticket_sqlalchemy(ticket_id, df_analistas)
        except Exception as e:
            st.error(f'❌ Erro ao renderizar árvore: {e}')

    separador()

    # Exportar
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df_movs_ok, 'roteamento_movimentacoes',
                        key='export_roteamento_prod_rot')
