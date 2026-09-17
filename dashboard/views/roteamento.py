# ============================================================
# dashboard/pages/roteamento.py
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
)
from config import COR_BAR, COR_DANGER, COR_TEXT_SEC, CAMINHO_BANCO


def render(df):
    page_header('Roteamento', 'e Gargalos',
                'Fluxo dos tickets entre analistas e identificação de gargalos.')

    # ---------- Carrega movimentações e mensagens ----------
    from data import carregar_movimentacoes, carregar_mensagens
    movs = carregar_movimentacoes()
    msgs = carregar_mensagens()

    if movs.empty:
        callout('warning', 'Atenção',
                'Sem movimentações. Rode o Programa5 para enriquecer os tickets.')
        return

    movs_ok = movs.dropna(subset=['autor']).copy()

    # ---------- KPIs ----------
    total_tickets = movs_ok['ticket_id'].nunique()
    pessoas_por_ticket = movs_ok.groupby('ticket_id')['autor'].nunique()
    media_pessoas = pessoas_por_ticket.mean() if not pessoas_por_ticket.empty else 0
    msgs_total = len(msgs)
    tickets_alto = len(pessoas_por_ticket[pessoas_por_ticket >= 5])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi('Tickets Enriquecidos', f'{total_tickets}')
    with col2:
        kpi('Média de Pessoas/Ticket', f'{media_pessoas:.1f}',
            pill='Alto' if media_pessoas > 3.5 else 'OK',
            pill_tipo='negative' if media_pessoas > 3.5 else 'positive')
    with col3:
        kpi('Mensagens Capturadas', f'{msgs_total}')
    with col4:
        kpi('Tickets com 5+ Pessoas', f'{tickets_alto}',
            pill='Atenção' if tickets_alto > 5 else 'OK',
            pill_tipo='negative' if tickets_alto > 5 else 'positive')

    separador()

    # ---------- Quantas pessoas por ticket + Top quem movimenta ----------
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
        top_mov = movs_ok.groupby('autor').size()\
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

    # ---------- Maiores gaps entre movimentações ----------
    painel_title('Maiores <b>Gaps entre Movimentações</b>')
    st.markdown(
        '<div class="page-caption" style="margin-top:-14px;">'
        'Onde os tickets ficaram mais tempo parados</div>',
        unsafe_allow_html=True,
    )

    movs_sorted = movs_ok.sort_values(['ticket_id', 'data_movimentacao']).copy()
    movs_sorted['data_anterior'] = (
        movs_sorted.groupby('ticket_id')['data_movimentacao'].shift(1)
    )
    movs_sorted['horas_parado'] = (
        movs_sorted['data_movimentacao'] - movs_sorted['data_anterior']
    ).dt.total_seconds() / 3600

    gaps = movs_sorted.dropna(subset=['horas_parado'])
    gaps = gaps[gaps['horas_parado'] > 24].copy()
    gaps['dias_parado'] = (gaps['horas_parado'] / 24).round(1)

    if not gaps.empty:
        top_gaps = gaps.nlargest(15, 'horas_parado')[
            ['ticket_id', 'autor', 'dias_parado']
        ].copy()
        top_gaps.columns = ['Ticket', 'Quem recebeu', 'Dias parado']
        st.dataframe(top_gaps, use_container_width=True, hide_index=True)

        # ---------- Distribuição de gaps ----------
        st.markdown('')
        painel_title('Distribuição de <b>Gaps</b>')

        bins = pd.cut(
            gaps['dias_parado'],
            bins=[0, 2, 3, 7, 14, 30, 9999],
            labels=['1-2d', '2-3d', '3-7d', '7-14d', '14-30d', '30d+'],
        )
        dist = bins.value_counts().sort_index().reset_index()
        dist.columns = ['faixa', 'qtd']

        hbar_list([
            {'label': r['faixa'],
             'value': int(r['qtd']),
             'formatted': str(int(r['qtd'])),
             'accent': r['faixa'] in ['14-30d', '30d+']}
            for _, r in dist.iterrows()
        ])

        mediana = gaps['dias_parado'].median()
        grandes = len(gaps[gaps['dias_parado'] > 7])

        if mediana > 3:
            callout(
                'warning', 'Atenção',
                f'Mediana de dias entre movimentações é <b>{mediana:.1f} dias</b>. '
                f'<b>{grandes} tickets</b> tiveram gap > 7 dias.'
            )
        else:
            callout(
                'success', 'OK',
                f'Mediana de dias entre movimentações é <b>{mediana:.1f} dias</b>.'
            )
    else:
        callout('info', 'Info', 'Sem gaps relevantes (> 1 dia) identificados.')

    separador()

    # ---------- Top quem escreve mensagens ----------
    if not msgs.empty:
        painel_title('Top <b>Quem Mais Escreve Mensagens</b>')
        top_msg = msgs.dropna(subset=['autor']).groupby('autor').size()\
            .sort_values(ascending=False).head(10).reset_index()
        top_msg.columns = ['autor', 'qtd']

        hbar_list([
            {'label': r['autor'][:25],
             'value': int(r['qtd']),
             'formatted': str(int(r['qtd']))}
            for _, r in top_msg.iterrows()
        ])

        # Insight sobre mensagens
        media_msg = msgs.groupby('ticket_id').size().mean()
        if media_msg > 3:
            callout(
                'warning', 'Atenção',
                f'Média de <b>{media_msg:.1f} mensagens por ticket</b> — '
                f'indica alto nível de comunicação/encaminhamento.'
            )