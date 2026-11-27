# ============================================================
# dashboard/views/sla_reincidencia.py — SLA + Reincidência
# ============================================================
"""
Página unificada de SLA e Reincidência (Fase 3 — Etapa 2).

Combina:
  - SLA: cumprimento, estourado, em andamento, em risco, por categoria/prioridade
  - Reincidência: tickets reabertos, taxa de reabertura, eventos de reabertura
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from services.sla_service import (
    calcular_metricas_sla,
    calcular_sla_por_categoria,
    calcular_sla_por_prioridade,
    calcular_margem_media,
    tickets_em_risco,
    aplicar_sla_status,
)
from services.reopening_service import (
    detectar_reaberturas,
    calcular_metricas_reabertura,
    enriquecer_tickets_com_reaberturas,
)
from components import (
    kpi, callout, separador, hbar_list, painel_title,
    aplicar_tema_plotly, botao_exportar, legenda_grafico,
    info_grafico, chart_card, card_com_tabela, card_com_barras,
    global_header, empty_state, insight_card,
    BADGES_PRIORIDADE, BADGES_SLA, BADGES_STATUS,
)
from lucide import lucide
from config import COR_SUCCESS, COR_DANGER


def render(df_filtrado: pd.DataFrame):
    # ==================== HEADER ====================
    global_header(
        'SLA + Reincidência',
        'Cumprimento de prazos e identificação de tickets reabertos.',
        usuario=st.session_state.get('usuario'),
    )

    df = df_filtrado.copy()

    # ==================== APLICA REGRAS DE SLA ====================
    df = aplicar_sla_status(df)

    # Carrega movimentações para detecção de reabertura
    from data import carregar_movimentacoes
    df_movs = carregar_movimentacoes()

    # ==================== KPIs GERAIS ====================
    metrica_sla = calcular_metricas_sla(df)

    # Detecta reaberturas a partir das movimentações
    df_reab = detectar_reaberturas(df_movs)
    metrica_reab = calcular_metricas_reabertura(df, df_reab)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi(
            'Total com SLA',
            f'{metrica_sla["total"]}',
            icone='target',
        )
    with col2:
        kpi(
            '% Cumprido',
            f'{metrica_sla["percentual_cumprido"]:.1f}%',
            pill=f'{metrica_sla["cumpridos"]} tickets',
            pill_tipo='positive' if metrica_sla['percentual_cumprido'] >= 80 else 'negative',
            icone='check-circle',
        )
    with col3:
        kpi(
            'Estourados',
            f'{metrica_sla["estourados"]}',
            pill=f'{metrica_sla["percentual_estourado"]:.0f}%',
            pill_tipo='negative' if metrica_sla['estourados'] > 0 else 'neutral',
            icone='alert-triangle',
        )
    with col4:
        kpi(
            'Tickets Reabertos',
            f'{metrica_reab["tickets_reabertos"]}',
            pill=f'{metrica_reab["taxa_reabertura"]:.1f}% taxa',
            pill_tipo='negative' if metrica_reab['taxa_reabertura'] > 10 else 'positive',
            icone='refresh-ccw',
        )

    # Reconciliação do denominador: SLA só é calculável para resolvidos COM previsão
    excluidos = metrica_sla['em_andamento'] + metrica_sla['sem_previsao']
    if excluidos > 0:
        st.caption(
            f'ℹ️ "Total com SLA" considera apenas tickets resolvidos com previsão válida '
            f'({metrica_sla["total"]} de {len(df)}). '
            f'{excluidos} ticket(s) fora do cálculo: '
            f'{metrica_sla["em_andamento"]} ainda em andamento (não resolvidos) e '
            f'{metrica_sla["sem_previsao"]} sem previsão definida.'
        )

    separador()

    # ==================== SEÇÃO SLA ====================
    st.markdown('## 📊 SLA — Acordo de Nível de Serviço')

    df_sla = df[df['sla_status'].isin(['cumprido', 'estourado'])].copy()

    if df_sla.empty:
        empty_state(
            titulo='Sem tickets com SLA definido',
            descricao='Nenhum ticket tem prazo definido no período selecionado.',
            icone='target',
        )
    else:
        col_esq, col_dir = st.columns(2)

        with col_esq:
            card_com_barras(
                titulo='Status Geral',
                descricao='Distribuição de cumprimento',
                icone='pie-chart',
                items=[
                    {'label': 'Cumprido',
                     'value': metrica_sla['cumpridos'],
                     'formatted': f'{metrica_sla["cumpridos"]} · {metrica_sla["percentual_cumprido"]:.1f}%'},
                    {'label': 'Estourado',
                     'value': metrica_sla['estourados'],
                     'formatted': f'{metrica_sla["estourados"]} · {metrica_sla["percentual_estourado"]:.1f}%',
                     'accent': True},
                ],
            )
            legenda_grafico([
                {'cor': '#2ecc71', 'label': 'Cumprido'},
                {'cor': '#e74c3c', 'label': 'Estourado'},
            ])

        with col_dir:
            sla_por_prioridade = calcular_sla_por_prioridade(df)
            if not sla_por_prioridade.empty:
                ordem = ['Urgente', 'Alta', 'Média', 'Média-1', 'Média-2',
                         'Baixa', 'Baixa-1', 'Baixa-2', 'Baixa-3']
                sla_por_prioridade['ordem'] = sla_por_prioridade['prioridade'].map(
                    {p: i for i, p in enumerate(ordem)}
                ).fillna(99)
                sla_por_prioridade = sla_por_prioridade.sort_values('ordem')

                card_com_barras(
                    titulo='SLA por Prioridade',
                    descricao='% de cumprimento por criticidade',
                    icone='bar-chart',
                    items=[
                        {'label': r['prioridade'],
                         'value': float(r['percentual']),
                         'formatted': f'{r["percentual"]:.1f}%',
                         'accent': r['percentual'] < 80}
                        for _, r in sla_por_prioridade.iterrows()
                    ],
                )

    # Tickets em risco
    tickets_risco = tickets_em_risco(df, dias_limite=2)
    if not tickets_risco.empty:
        callout(
            'warning', 'Atenção — Tickets em Risco',
            f'{len(tickets_risco)} ticket(s) próximo(s) do vencimento ou já '
            f'fora do prazo e ainda não resolvido(s).',
        )
        st.dataframe(
            tickets_risco[['id', 'titulo', 'categoria', 'prioridade', 'previsao', 'status']]
            .head(10),
            use_container_width=True,
            hide_index=True,
            column_config={
                'previsao': st.column_config.DatetimeColumn('Previsão'),
            },
        )

    # Margem média
    margem_media = calcular_margem_media(df)
    if margem_media != 0.0:
        sinal = '+' if margem_media > 0 else ''
        cor_margem = 'positive' if margem_media > 0 else 'negative'
        kpi(
            'Margem Média',
            f'{sinal}{margem_media:.1f}d',
            pill_tipo=cor_margem,
            icone='clock',
        )

    separador()

    # ==================== SEÇÃO REINCIDÊNCIA ====================
    st.markdown('## 🔄 Reincidência — Tickets Reabertos')

    if df_movs.empty:
        callout('info', 'Info',
                'Sem movimentações capturadas. Execute o pipeline de enriquecimento '
                'para habilitar a detecção de reaberturas.')
    else:
        df_reab = detectar_reaberturas(df_movs)

        if df_reab.empty:
            callout('success', 'OK',
                    'Nenhum ticket foi reaberto após ser marcado como '
                    'Resolvido ou Fechado.')
        else:
            # Enriquece com dados do ticket
            df_tickets_com_reab = enriquecer_tickets_com_reaberturas(df, df_reab)
            df_reab_filtrado = df_tickets_com_reab[
                df_tickets_com_reab['reaberto_vezes'] > 0
            ].copy()

            if df_reab_filtrado.empty:
                callout('success', 'OK',
                        'Nenhum ticket foi reaberto no período filtrado.')
            else:
                col_a, col_b = st.columns(2)

                with col_a:
                    painel_title('Quantas vezes <b>cada ticket reabriu</b>')
                    dist_reab = df_reab_filtrado['reaberto_vezes'].value_counts()\
                        .sort_index().reset_index()
                    dist_reab.columns = ['vezes', 'qtd']
                    hbar_list([
                        {'label': f'{int(r["vezes"])}x',
                         'value': int(r['qtd']),
                         'formatted': str(int(r['qtd'])),
                         'accent': r['vezes'] >= 3}
                        for _, r in dist_reab.iterrows()
                    ])

                with col_b:
                    painel_title('Top <b>responsáveis</b> com reaberturas')
                    top_resp = df_reab_filtrado.groupby('responsavel_atual').agg(
                        reabertos=('ticket_id', 'nunique'),
                        total_reaberturas=('reaberto_vezes', 'sum'),
                    ).reset_index()
                    top_resp = top_resp.sort_values('reabertos', ascending=False).head(10)
                    hbar_list([
                        {'label': str(r['responsavel_atual'])[:22],
                         'value': int(r['reabertos']),
                         'formatted': f'{int(r["reabertos"])} ({int(r["total_reaberturas"])}x)',
                         'accent': r['reabertos'] >= 3}
                        for _, r in top_resp.iterrows()
                    ])

                # Tabela detalhada
                painel_title('Tickets <b>reabertos</b> — detalhamento')
                tabela = df_reab_filtrado.nlargest(30, 'reaberto_vezes')[
                    ['id', 'titulo', 'categoria', 'status',
                     'responsavel_atual', 'reaberto_vezes',
                     'data_primeira_reabertura', 'data_ultima_reabertura']
                ].copy()
                tabela.columns = [
                    'ID', 'Título', 'Categoria', 'Status',
                    'Responsável', 'Reaberto (vezes)',
                    'Primeira Reabertura', 'Última Reabertura',
                ]
                tabela['Primeira Reabertura'] = pd.to_datetime(
                    tabela['Primeira Reabertura'], errors='coerce'
                ).dt.strftime('%d/%m/%Y %H:%M').fillna('—')
                tabela['Última Reabertura'] = pd.to_datetime(
                    tabela['Última Reabertura'], errors='coerce'
                ).dt.strftime('%d/%m/%Y %H:%M').fillna('—')

                st.dataframe(tabela, use_container_width=True, hide_index=True)

    # ==================== EXPORTAR ====================
    separador()
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        df_export = df_sla if not df_sla.empty else df
        botao_exportar(df_export, 'sla_reincidencia', key='export_sla_reincidencia')
