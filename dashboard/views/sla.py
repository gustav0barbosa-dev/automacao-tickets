# ============================================================
# dashboard/pages/sla.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
    botao_exportar,
)
from config import COR_SUCCESS, COR_DANGER


def render(df):
    page_header('SLA —', 'Acordo de Nível de Serviço',
                'Cumprimento dos prazos acordados.')

    # ---------- Filtra só tickets com SLA definido ----------
    df_sla = df[
        df['previsao'].notna() &
        df['sla_status'].isin(['cumprido', 'estourado'])
    ].copy()

    if df_sla.empty:
        callout('warning', 'Atenção', 'Sem tickets com SLA definido no período.')
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

    # ---------- KPIs ----------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Total com SLA', f'{total}')
    with col2:
        kpi('% Cumprido', f'{perc:.1f}%',
            pill=f'{cumpridos} tickets',
            pill_tipo='positive')
    with col3:
        kpi('Estourados', f'{estourados}',
            pill=f'{estourados/total*100:.0f}%',
            pill_tipo='negative' if estourados > 0 else 'neutral')
    with col4:
        kpi('Margem Média', f'{margem_media:+.1f}d',
            pill_tipo='positive' if margem_media > 0 else 'negative')

    separador()

    # ---------- Geral + Prioridade ----------
    col_esq, col_dir = st.columns(2)

    with col_esq:
        painel_title('Status <b>Geral</b>')
        hbar_list([
            {'label': 'Cumprido', 'value': cumpridos,
             'formatted': f'{cumpridos} · {perc:.1f}%'},
            {'label': 'Estourado', 'value': estourados,
             'formatted': f'{estourados} · {100-perc:.1f}%',
             'accent': True},
        ])

    with col_dir:
        painel_title('SLA por <b>Prioridade</b>')
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

        hbar_list([
            {'label': r['prioridade'],
             'value': float(r['perc']),
             'formatted': f'{r["perc"]:.1f}%',
             'accent': r['prioridade'] == 'Crítica' and r['perc'] < 80}
            for _, r in prio_sla.iterrows()
        ])

    separador()

    # ---------- Ranking por categoria ----------
    painel_title('Ranking por <b>Categoria</b>')
    cat_sla = df_sla.groupby('categoria').agg(
        total=('id', 'count'),
        cumpridos=('sla_status', lambda x: (x == 'cumprido').sum()),
    ).reset_index()
    cat_sla = cat_sla[cat_sla['total'] >= 3].copy()
    cat_sla['perc'] = cat_sla['cumpridos'] / cat_sla['total'] * 100
    cat_sla = cat_sla.sort_values('perc')

    if not cat_sla.empty:
        hbar_list([
            {'label': r['categoria'],
             'value': float(r['perc']),
             'formatted': f'{r["perc"]:.1f}%',
             'accent': r['perc'] < 70}
            for _, r in cat_sla.iterrows()
        ])

        pior = cat_sla.iloc[0]
        if pior['perc'] < 80:
            callout(
                'warning', 'Atenção',
                f'Categoria <b>{pior["categoria"]}</b> tem apenas '
                f'<b>{pior["perc"]:.1f}%</b> de SLA cumprido '
                f'({int(pior["cumpridos"])}/{int(pior["total"])} tickets).'
            )

    separador()

    # ---------- Distribuição de margem ----------
    painel_title('Distribuição da <b>Margem</b> (dias antes/depois do prazo)')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Valores negativos = SLA estourado · Positivos = cumprido com folga</div>',
        unsafe_allow_html=True,
    )

    df_margem = df_sla.dropna(subset=['margem_dias'])
    if not df_margem.empty:
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

    # ---------- Insight final ----------
    if perc >= 95:
        callout('success', 'OK',
                f'SLA global em <b>{perc:.1f}%</b> — meta atingida.')
    elif perc >= 80:
        callout('info', 'Insight',
                f'SLA global em <b>{perc:.1f}%</b> — aceitável, mas há espaço para melhoria.')
    else:
        callout('warning', 'Atenção',
                f'SLA global em <b>{perc:.1f}%</b> — abaixo da meta recomendada (95%).')

    separador()

    # ==================== SLA POR CRITICIDADE ====================
    painel_title('SLA por <b>Criticidade</b>')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Prazo ideal por criticidade: Urgente=3d, Alta=5d, '
                'Média=10d, Baixa=15d (dias úteis)'
                '</div>',
                unsafe_allow_html=True)

    # Verifica se a coluna existe
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
                kpi('Total com Criticidade', f'{total_crit}')

            with col2:
                cumpridos = (df_crit['sla_criticidade_ok'] == 1).sum()
                perc = (cumpridos / total_crit * 100) if total_crit else 0
                kpi('% Cumprido', f'{perc:.1f}%',
                    pill=f'{cumpridos} tickets',
                    pill_tipo='positive' if perc >= 80 else 'negative')

            with col3:
                media_dias = df_crit['dias_uteis_resolucao'].mean()
                kpi('Média Dias Úteis', f'{media_dias:.1f}d')

            st.markdown('')

            # ---------- Gráficos ----------
            col_a, col_b = st.columns(2)

            with col_a:
                painel_title('Cumprimento por <b>Criticidade</b>')

                agg = df_crit.groupby('prioridade').agg(
                    total=('id', 'count'),
                    ok=('sla_criticidade_ok', 'sum'),
                ).reset_index()
                agg['perc'] = (agg['ok'] / agg['total'] * 100).round(1)

                # Ordem customizada
                ordem = ['Urgente', 'Alta', 'Média', 'Média 1', 'Média 2',
                         'Média-1', 'Média-2', 'Baixa', 'Baixa 1', 'Baixa 2',
                         'Baixa-1', 'Baixa-2', 'Baixa-3']
                agg['ordem'] = agg['prioridade'].map(
                    {p: i for i, p in enumerate(ordem)}
                ).fillna(99)
                agg = agg.sort_values('ordem')

                hbar_list([
                    {'label': r['prioridade'],
                     'value': float(r['perc']),
                     'formatted': f'{r["perc"]:.1f}% ({int(r["ok"])}/{int(r["total"])})',
                     'accent': r['perc'] < 80}
                    for _, r in agg.iterrows()
                ])

            with col_b:
                painel_title('Média de <b>Dias Úteis</b> até Resolução')

                media_dias_prio = df_crit.groupby('prioridade')[
                    'dias_uteis_resolucao'
                ].mean().reset_index()

                media_dias_prio['ordem'] = media_dias_prio['prioridade'].map(
                    {p: i for i, p in enumerate(ordem)}
                ).fillna(99)
                media_dias_prio = media_dias_prio.sort_values('ordem').dropna()

                # Mapeia prazo ideal
                prazo_ideal = {
                    'Urgente': 3, 'Alta': 5,
                    'Média': 10, 'Média 1': 10, 'Média 2': 10,
                    'Média-1': 10, 'Média-2': 10,
                    'Baixa': 15, 'Baixa 1': 15, 'Baixa 2': 15,
                    'Baixa-1': 15, 'Baixa-2': 15, 'Baixa-3': 15,
                }

                if not media_dias_prio.empty:
                    hbar_list([
                        {'label': f'{r["prioridade"]} (ideal: {prazo_ideal.get(r["prioridade"], "?")}d)',
                         'value': float(r['dias_uteis_resolucao']),
                         'formatted': f'{r["dias_uteis_resolucao"]:.1f}d',
                         'accent': r['dias_uteis_resolucao'] > prazo_ideal.get(r['prioridade'], 99)}
                        for _, r in media_dias_prio.iterrows()
                    ])

            # ---------- Insights ----------
            st.markdown('')

            if not agg.empty:
                pior = agg.iloc[0]
                melhor = agg.iloc[-1]

                if pior['perc'] < 70:
                    callout('warning', 'Atenção',
                            f'Criticidade <b>{pior["prioridade"]}</b> tem apenas '
                            f'<b>{pior["perc"]:.1f}%</b> de SLA cumprido '
                            f'({int(pior["ok"])}/{int(pior["total"])} tickets).')

                # Urgente abaixo de 90%
                urgente = agg[agg['prioridade'] == 'Urgente']
                if not urgente.empty and urgente.iloc[0]['perc'] < 90:
                    callout('warning', 'Crítico',
                            f'Tickets <b>Urgente</b> estão em '
                            f'<b>{urgente.iloc[0]["perc"]:.1f}%</b> — '
                            f'deveria ser próximo de 100%.')

                callout('info', 'Insight',
                        f'Melhor desempenho: <b>{melhor["prioridade"]}</b> '
                        f'({melhor["perc"]:.1f}%).')

    separador()
    
    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        botao_exportar(df_sla, 'sla', key='export_sla')