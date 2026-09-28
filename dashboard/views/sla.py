# ============================================================
# dashboard/views/sla.py — refatorado (Fase 5)
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

from components import (
    kpi, callout, separador, hbar_list, painel_title,
    aplicar_tema_plotly, botao_exportar, legenda_grafico,
    info_grafico, chart_card, card_com_tabela, card_com_barras,
    global_header, empty_state, insight_card,
    BADGES_PRIORIDADE, BADGES_SLA, BADGES_STATUS,
)
from lucide import lucide
from config import COR_SUCCESS, COR_DANGER


def render(df):
    # ==================== HEADER ====================
    global_header(
        'SLA — Acordo de Nível de Serviço',
        'Cumprimento dos prazos acordados.',
        usuario=st.session_state.get('usuario'),
    )

    # ---------- Filtra só tickets com SLA definido ----------
    df_sla = df[
        df['previsao'].notna() &
        df['sla_status'].isin(['cumprido', 'estourado'])
    ].copy()

    if df_sla.empty:
        empty_state(
            titulo='Sem tickets com SLA definido',
            descricao='Nenhum ticket tem prazo definido no período selecionado.',
            icone='target',
        )
        return

    cumpridos = len(df_sla[df_sla['sla_status'] == 'cumprido'])
    estourados = len(df_sla[df_sla['sla_status'] == 'estourado'])
    total = len(df_sla)
    perc = cumpridos / total * 100 if total > 0 else 0

    # Margem
    df_sla['margem_dias'] = (
        df_sla['previsao'] - df_sla['data_resolvido']
    ).dt.days
    margem_media = df_sla['margem_dias'].mean()

    # ==================== KPIs ====================
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Total com SLA', f'{total}', icone='target')
    with col2:
        kpi('% Cumprido', f'{perc:.1f}%',
            pill=f'{cumpridos} tickets',
            pill_tipo='positive',
            icone='check-circle')
    with col3:
        kpi('Estourados', f'{estourados}',
            pill=f'{estourados/total*100:.0f}%',
            pill_tipo='negative' if estourados > 0 else 'neutral',
            icone='alert-triangle')
    with col4:
        kpi('Margem Média', f'{margem_media:+.1f}d',
            pill_tipo='positive' if margem_media > 0 else 'negative',
            icone='clock')

    # ==================== STATUS GERAL + PRIORIDADE ====================
    col_esq, col_dir = st.columns(2)

    with col_esq:
        card_com_barras(
            titulo='Status Geral',
            descricao='Distribuição de cumprimento',
            icone='pie-chart',
            items=[
                {'label': 'Cumprido',
                 'value': cumpridos,
                 'formatted': f'{cumpridos} · {perc:.1f}%'},
                {'label': 'Estourado',
                 'value': estourados,
                 'formatted': f'{estourados} · {100-perc:.1f}%',
                 'accent': True},
            ],
        )

        legenda_grafico([
            {'cor': '#2ecc71', 'label': 'Cumprido'},
            {'cor': '#e74c3c', 'label': 'Estourado'},
        ])
        info_grafico(
            '<b>Cumprido</b> = ticket resolvido dentro do prazo. '
            '<b>Estourado</b> = resolvido após o prazo.'
        )

    with col_dir:
        prio_sla = df_sla.groupby('prioridade').agg(
            total=('id', 'count'),
            cumpridos=('sla_status', lambda x: (x == 'cumprido').sum()),
        ).reset_index()
        prio_sla['perc'] = prio_sla['cumpridos'] / prio_sla['total'] * 100

        ordem = ['Crítica', 'Alta', 'Média', 'Baixa-1', 'Baixa-2', 'Baixa-3']
        prio_sla['ordem'] = prio_sla['prioridade'].map(
            {p: i for i, p in enumerate(ordem)}
        ).fillna(99)
        prio_sla = prio_sla.sort_values('ordem')

        card_com_barras(
            titulo='SLA por Prioridade',
            descricao='% de cumprimento por criticidade',
            icone='bar-chart',
            items=[
                {'label': r['prioridade'],
                 'value': float(r['perc']),
                 'formatted': f'{r["perc"]:.1f}%',
                 'accent': r['prioridade'] == 'Crítica' and r['perc'] < 80}
                for _, r in prio_sla.iterrows()
            ],
        )

    # ==================== RANKING POR CATEGORIA ====================
    cat_sla = df_sla.groupby('categoria').agg(
        total=('id', 'count'),
        cumpridos=('sla_status', lambda x: (x == 'cumprido').sum()),
    ).reset_index()
    cat_sla = cat_sla[cat_sla['total'] >= 3].copy()
    cat_sla['perc'] = cat_sla['cumpridos'] / cat_sla['total'] * 100
    cat_sla = cat_sla.sort_values('perc')

    if not cat_sla.empty:
        card_com_barras(
            titulo='Ranking por Categoria',
            descricao='% de cumprimento por categoria',
            icone='bar-chart',
            items=[
                {'label': r['categoria'],
                 'value': float(r['perc']),
                 'formatted': f'{r["perc"]:.1f}%',
                 'accent': r['perc'] < 70}
                for _, r in cat_sla.iterrows()
            ],
        )

        pior = cat_sla.iloc[0]
        if pior['perc'] < 80:
            callout(
                'warning', 'Atenção',
                f'Categoria <b>{pior["categoria"]}</b> tem apenas '
                f'<b>{pior["perc"]:.1f}%</b> de SLA cumprido '
                f'({int(pior["cumpridos"])}/{int(pior["total"])} tickets).'
            )

    # ==================== DISTRIBUIÇÃO DE MARGEM ====================
    df_margem = df_sla.dropna(subset=['margem_dias'])
    if not df_margem.empty:
        with chart_card('Distribuição da Margem',
                        'Dias antes/depois do prazo — Negativos = estourado · Positivos = cumprido',
                        icone='bar-chart'):
            fig = px.histogram(
                df_margem,
                x='margem_dias',
                nbins=25,
                labels={'margem_dias': 'Dias (margem)'},
                color_discrete_sequence=[COR_SUCCESS],
            )
            fig = aplicar_tema_plotly(fig, altura=300)
            st.plotly_chart(fig, use_container_width=True,
                            config={'displayModeBar': False})

    # ==================== INSIGHTS ====================
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'margin:24px 0 14px 0;">'
        f'<span style="color:#c9a666;">{lucide("alert-triangle", 18)}</span>'
        f'<span style="font-family:Fraunces,serif;font-size:18px;font-weight:600;">'
        f'Insights e Alertas</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_i1, col_i2, col_i3 = st.columns(3)

    with col_i1:
        if perc >= 95:
            insight_card('success', 'SLA Global', f'{perc:.0f}%', 'Meta atingida')
        elif perc >= 80:
            insight_card('warning', 'SLA Global', f'{perc:.0f}%', 'Aceitável')
        else:
            insight_card('danger', 'SLA Global', f'{perc:.0f}%', 'Abaixo da meta')

    with col_i2:
        insight_card('info', 'Cumpridos', f'{cumpridos}', 'tickets no prazo')

    with col_i3:
        insight_card('warning' if estourados > 0 else 'success',
                     'Estourados', f'{estourados}', 'tickets fora do prazo')

    # ==================== SLA POR CRITICIDADE ====================
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;'
        f'margin:24px 0 14px 0;">'
        f'<span style="color:#c9a666;">{lucide("target", 18)}</span>'
        f'<span style="font-family:Fraunces,serif;font-size:18px;font-weight:600;">'
        f'SLA por Criticidade</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="font-size:12.5px;color:#5c6270;margin-bottom:14px;">'
        'Prazo ideal por criticidade (horas úteis): '
        '<b>Urgente</b>=3h · <b>Alta</b>=24h · '
        '<b>Média</b>=48h · <b>Média-2</b>=72h · '
        '<b>Baixa</b>=120h · <b>Baixa-2</b>=168h'
        '</div>',
        unsafe_allow_html=True,
    )

    if 'sla_criticidade_ok' not in df.columns:
        callout('info', 'Info',
                'Sem cálculo de criticidade. Rode '
                '`python scripts/analisar_sla_criticidade.py`.')
    else:
        df_crit = df[df['sla_criticidade_ok'].notna()].copy()

        if df_crit.empty:
            callout('info', 'Info',
                    'Sem tickets resolvidos com prazo definido.')
        else:
            # ---------- KPIs ----------
            col1, col2, col3 = st.columns(3)
            with col1:
                total_crit = len(df_crit)
                kpi('Total com Criticidade', f'{total_crit}', icone='target')
            with col2:
                cumpridos_crit = (df_crit['sla_criticidade_ok'] == 1).sum()
                perc_crit = (cumpridos_crit / total_crit * 100) if total_crit else 0
                kpi('% Cumprido', f'{perc_crit:.1f}%',
                    pill=f'{cumpridos_crit} tickets',
                    pill_tipo='positive' if perc_crit >= 80 else 'negative',
                    icone='check-circle')
            with col3:
                media_horas = df_crit['horas_resolucao'].mean()
                kpi('Média Horas Úteis', f'{media_horas:.1f}h', icone='clock')

            # ---------- Gráficos ----------
            col_a, col_b = st.columns(2)

            with col_a:
                agg = df_crit.groupby('prioridade').agg(
                    total=('id', 'count'),
                    ok=('sla_criticidade_ok', 'sum'),
                ).reset_index()
                agg['perc'] = (agg['ok'] / agg['total'] * 100).round(1)

                ordem = ['Urgente', 'Alta', 'Média', 'Média 1', 'Média 2',
                         'Média-1', 'Média-2', 'Baixa', 'Baixa 1', 'Baixa 2',
                         'Baixa-1', 'Baixa-2', 'Baixa-3']
                agg['ordem'] = agg['prioridade'].map(
                    {p: i for i, p in enumerate(ordem)}
                ).fillna(99)
                agg = agg.sort_values('ordem')

                card_com_barras(
                    titulo='Cumprimento por Criticidade',
                    descricao='% de SLA cumprido por prioridade',
                    icone='bar-chart',
                    items=[
                        {'label': r['prioridade'],
                         'value': float(r['perc']),
                         'formatted': f'{r["perc"]:.1f}% ({int(r["ok"])}/{int(r["total"])})',
                         'accent': r['perc'] < 80}
                        for _, r in agg.iterrows()
                    ],
                )

            with col_b:
                media_dias_prio = df_crit.groupby('prioridade')[
                    'horas_resolucao'
                ].mean().reset_index()

                media_dias_prio['ordem'] = media_dias_prio['prioridade'].map(
                    {p: i for i, p in enumerate(ordem)}
                ).fillna(99)
                media_dias_prio = media_dias_prio.sort_values('ordem').dropna()

                prazo_ideal = {
                    'Urgente': 3, 'Alta': 24,
                    'Média': 48, 'Média 1': 48, 'Média 2': 72,
                    'Média-1': 48, 'Média-2': 72,
                    'Baixa': 120, 'Baixa 1': 120, 'Baixa 2': 168,
                    'Baixa-1': 120, 'Baixa-2': 168, 'Baixa-3': 168,
                }

                if not media_dias_prio.empty:
                    card_com_barras(
                        titulo='Média de Horas Úteis até Resolução',
                        descricao='Tempo médio por criticidade',
                        icone='clock',
                        items=[
                            {'label': f'{r["prioridade"]} (ideal: {prazo_ideal.get(r["prioridade"], "?")}h)',
                             'value': float(r['horas_resolucao']),
                             'formatted': f'{r["horas_resolucao"]:.1f}h',
                             'accent': r['horas_resolucao'] > prazo_ideal.get(r['prioridade'], 999)}
                            for _, r in media_dias_prio.iterrows()
                        ],
                    )

    # ==================== EXPORTAR ====================
    separador()
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df_sla, 'sla', key='export_sla')