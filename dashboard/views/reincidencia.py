# ============================================================
# dashboard/views/reincidencia.py
# ============================================================
# Duas análises em uma única aba:
#
#   SEÇÃO 1 — FREQUÊNCIA POR SOLICITANTE
#       Quantos tickets cada pessoa abriu
#
#   SEÇÃO 2 — REABERTURA
#       Tickets que voltaram após "Resolvido" ou "Fechado"
# ============================================================

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import (
    page_header, kpi, callout, separador,
    hbar_list, painel_title, aplicar_tema_plotly,
    botao_exportar, legenda_grafico, info_grafico,
)
from config import COR_GOLD, COR_SUCCESS, COR_DANGER, COR_WARNING
from data import carregar_movimentacoes


# ============================================================
# ANÁLISE DE REABERTURA
# ============================================================
def detectar_reaberturas(df_movs, data_inicio=None, data_fim=None):
    """
    Detecta tickets reabertos usando de_status e para_status.
    
    Reabertura = de_status em ('Resolvido', 'Fechado')
             E para_status em ('Em atendimento', 'Aguardando confirmação do usuário')
    """
    if df_movs.empty:
        return pd.DataFrame(columns=[
            'ticket_id', 'reaberto_vezes',
            'data_primeira_reabertura', 'data_ultima_reabertura'
        ])

    df = df_movs.copy()
    df['data_movimentacao'] = pd.to_datetime(df['data_movimentacao'], errors='coerce')

    # Normaliza strings (remove espaços, converte para str)
    df['de_status'] = df['de_status'].astype(str).str.strip()
    df['para_status'] = df['para_status'].astype(str).str.strip()
    df['ticket_id'] = df['ticket_id'].astype(str)

    # Filtro de reabertura
    status_reaberto = ['Resolvido', 'Fechado']
    status_voltou = ['Em atendimento', 'Aguardando confirmação do usuário']

    df_reab = df[
        df['de_status'].isin(status_reaberto) &
        df['para_status'].isin(status_voltou)
    ].copy()

    if df_reab.empty:
        return pd.DataFrame(columns=[
            'ticket_id', 'reaberto_vezes',
            'data_primeira_reabertura', 'data_ultima_reabertura'
        ])

    resultado = df_reab.groupby('ticket_id').agg(
        reaberto_vezes=('id', 'count'),
        data_primeira_reabertura=('data_movimentacao', 'min'),
        data_ultima_reabertura=('data_movimentacao', 'max'),
    ).reset_index()

    return resultado


# ============================================================
# RENDER
# ============================================================
def render(df):
    page_header('Reincidência', 'de Tickets',
                'Análise de frequência por solicitante e reabertura de tickets.')

    # ============================================================
    # SEÇÃO 1 — FREQUÊNCIA POR SOLICITANTE
    # ============================================================
    st.markdown('## 📊 Seção 1 — Frequência por Solicitante')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Quantos tickets cada pessoa abriu no período filtrado'
                '</div>',
                unsafe_allow_html=True)

    # Filtra solicitantes válidos
    df_sol = df[
        df['solicitante'].notna() &
        (df['solicitante'] != '') &
        (df['solicitante'] != 'Não informado')
    ].copy()

    if df_sol.empty:
        callout('warning', 'Atenção', 'Sem solicitantes identificados no período.')
    else:
        # Agrega por solicitante
        agg = df_sol.groupby('solicitante').agg(
            total=('id', 'count'),
            primeiro=('criado_data', 'min'),
            ultimo=('criado_data', 'max'),
            categorias=('categoria', lambda x: x.nunique()),
        ).reset_index()
        agg.columns = ['Solicitante', 'Total', 'Primeiro', 'Último', 'Categorias']

        # KPIs
        total_solicitantes = len(agg)
        reincidentes = len(agg[agg['Total'] >= 2])
        muito_reincidentes = len(agg[agg['Total'] >= 5])
        taxa = (reincidentes / total_solicitantes * 100) if total_solicitantes else 0
        media = agg['Total'].mean()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            kpi('Solicitantes Únicos', f'{total_solicitantes}')
        with col2:
            kpi('Com 2+ Tickets', f'{reincidentes}',
                pill=f'{taxa:.0f}%',
                pill_tipo='negative' if taxa > 30 else 'neutral')
        with col3:
            kpi('Média Tickets/Pessoa', f'{media:.1f}')
        with col4:
            kpi('Com 5+ Tickets', f'{muito_reincidentes}',
                pill='⚠️ Atenção' if muito_reincidentes > 0 else 'OK',
                pill_tipo='negative' if muito_reincidentes > 0 else 'positive')

        st.markdown('')

        # Distribuição + Top 10
        col_a, col_b = st.columns(2)

        with col_a:
            painel_title('Distribuição de <b>tickets por solicitante</b>')
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
            painel_title('Top 10 <b>solicitantes</b>')
            top = agg.nlargest(10, 'Total').sort_values('Total')

            hbar_list([
                {'label': r['Solicitante'][:22],
                 'value': int(r['Total']),
                 'formatted': str(int(r['Total'])),
                 'accent': r['Total'] >= 5}
                for _, r in top.iterrows()
            ])

        # Insights
        if not agg.empty:
            top1 = agg.nlargest(1, 'Total').iloc[0]
            if top1['Total'] >= 5:
                callout('warning', 'Atenção',
                        f'<b>{top1["Solicitante"]}</b> abriu '
                        f'<b>{int(top1["Total"])} tickets</b> '
                        f'em {int(top1["Categorias"])} categoria(s).')

    separador()

    # ============================================================
    # SEÇÃO 2 — REABERTURA
    # ============================================================
    st.markdown('## 🔄 Seção 2 — Reabertura de Tickets')
    st.markdown('<div class="page-caption" style="margin-top:-14px;">'
                'Tickets que voltaram para "Em atendimento" após serem '
                'marcados como "Resolvido" ou "Fechado"'
                '</div>',
                unsafe_allow_html=True)

    # Carrega movimentações
    df_movs = carregar_movimentacoes()

    if df_movs.empty:
        callout('info', 'Info',
                'Sem movimentações capturadas. Execute o Programa5 para enriquecer.')
    else:
        # Detecta reaberturas (SEM filtro de período)
        df_reab = detectar_reaberturas(df_movs)

        # ---------- NORMALIZA TIPOS (correção do bug) ----------
        if not df_reab.empty:
            df_reab['ticket_id'] = df_reab['ticket_id'].astype(str)
            ids_filtrados = set(df['id'].astype(str).tolist())
            df_reab_filtrado = df_reab[df_reab['ticket_id'].isin(ids_filtrados)].copy()
        else:
            df_reab_filtrado = df_reab

        # KPIs
        total_tickets = len(df)
        reabertos = len(df_reab_filtrado)
        total_reaberturas = df_reab_filtrado['reaberto_vezes'].sum() if not df_reab_filtrado.empty else 0
        taxa_reab = (reabertos / total_tickets * 100) if total_tickets else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            kpi('Tickets Reabertos', f'{reabertos}',
                ajuda=f'De {total_tickets} tickets filtrados')
        with col2:
            kpi('Taxa de Reabertura', f'{taxa_reab:.1f}%',
                pill='Alto' if taxa_reab > 10 else 'OK',
                pill_tipo='negative' if taxa_reab > 10 else 'positive')
        with col3:
            kpi('Total de Reaberturas', f'{int(total_reaberturas)}',
                ajuda='Soma de todas as reaberturas (um ticket pode reabrir várias vezes)')
        with col4:
            media_reab = df_reab_filtrado['reaberto_vezes'].mean() if not df_reab_filtrado.empty else 0
            kpi('Média por Ticket', f'{media_reab:.1f}x')

        st.markdown('')

        if df_reab_filtrado.empty:
            callout('success', 'OK',
                    'Nenhum ticket foi reaberto após ser marcado como Resolvido ou Fechado.')
        else:
            # Enriquecer com dados do ticket
            # Garante que o merge funcione (ambos como str)
            df_temp = df.copy()
            df_temp['id_str'] = df_temp['id'].astype(str)
            df_reab_full = df_reab_filtrado.merge(
                df_temp[['id_str', 'titulo', 'status', 'categoria', 'prioridade',
                        'responsavel_atual', 'responsavel_empresa']],
                left_on='ticket_id', right_on='id_str', how='left'
            )
            df_reab_full['id'] = df_reab_full['ticket_id']

            # ---------- Distribuição: quantas vezes cada ticket foi reaberto ----------
            col_a, col_b = st.columns(2)

            with col_a:
                painel_title('Quantas vezes <b>cada ticket reabriu</b>')
                dist_reab = df_reab_full['reaberto_vezes'].value_counts()\
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
                top_resp = df_reab_full.groupby('responsavel_atual').agg(
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

            st.markdown('')

            # ---------- Reabertura por categoria ----------
            painel_title('Reabertura por <b>categoria</b>')

            cat_reab = df_reab_full.groupby('categoria').agg(
                reabertos=('ticket_id', 'nunique'),
                total_reab=('reaberto_vezes', 'sum'),
            ).reset_index()
            cat_reab = cat_reab[cat_reab['reabertos'] >= 1]
            cat_reab = cat_reab.sort_values('reabertos', ascending=False).head(10)

            if not cat_reab.empty:
                hbar_list([
                    {'label': str(r['categoria'])[:30],
                     'value': int(r['reabertos']),
                     'formatted': f'{int(r["reabertos"])} ({int(r["total_reab"])}x)',
                     'accent': r['reabertos'] >= 3}
                    for _, r in cat_reab.iterrows()
                ])

            st.markdown('')

            # ---------- Tabela detalhada ----------
            painel_title('Tickets <b>reabertos</b> — detalhamento')

            tabela = df_reab_full.nlargest(30, 'reaberto_vezes')[
                ['ticket_id', 'titulo', 'categoria', 'status',
                 'responsavel_atual', 'reaberto_vezes',
                 'data_primeira_reabertura', 'data_ultima_reabertura']
            ].copy()

            tabela.columns = [
                'ID', 'Título', 'Categoria', 'Status',
                'Responsável', 'Reaberto (vezes)',
                'Primeira Reabertura', 'Última Reabertura'
            ]

            tabela['Primeira Reabertura'] = pd.to_datetime(
                tabela['Primeira Reabertura'], errors='coerce'
            ).dt.strftime('%d/%m/%Y %H:%M').fillna('—')

            tabela['Última Reabertura'] = pd.to_datetime(
                tabela['Última Reabertura'], errors='coerce'
            ).dt.strftime('%d/%m/%Y %H:%M').fillna('—')

            st.dataframe(tabela, use_container_width=True, hide_index=True)

            # Insights
            st.markdown('')
            pior_ticket = df_reab_full.nlargest(1, 'reaberto_vezes').iloc[0]
            if pior_ticket['reaberto_vezes'] >= 3:
                callout('warning', 'Atenção',
                        f'Ticket <b>#{pior_ticket["ticket_id"]}</b> '
                        f'(<b>{pior_ticket["titulo"][:50]}</b>) foi reaberto '
                        f'<b>{int(pior_ticket["reaberto_vezes"])} vezes</b>. '
                        f'Verifique o histórico.')

            if taxa_reab > 15:
                callout('warning', 'Atenção',
                        f'Taxa de reabertura em <b>{taxa_reab:.1f}%</b> — '
                        f'acima do ideal (10%). Pode indicar problema na qualidade da resolução.')

            st.markdown('')
            legenda_grafico([
                {'cor': COR_SUCCESS, 'label': 'Sem reabertura', 'tipo': 'circulo'},
                {'cor': COR_WARNING, 'label': '1-2 reaberturas', 'tipo': 'circulo'},
                {'cor': COR_DANGER, 'label': '3+ reaberturas', 'tipo': 'circulo'},
            ])

    # ============================================================
    # EXPORTAR
    # ============================================================
    separador()

    col_esq, col_dir = st.columns([4, 1])
    with col_dir:
        # Exporta um resumo consolidado
        df_export = df_sol if not df_sol.empty else pd.DataFrame()
        botao_exportar(df_export, 'reincidencia', key='export_reincidencia')