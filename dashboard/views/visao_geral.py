# ============================================================
# dashboard/views/visao_geral.py — Visão Geral (Dashboard Principal)
# ============================================================
"""
Tela principal do Help360 com resumo geral dos tickets.

Funcionalidades:
  1. Resumo geral: total de tickets, abertos, fechados, em andamento, SLA
  2. Distribuição de tickets por categoria
  3. Pesquisa por ticket específico com:
     - Informações detalhadas do ticket
     - Status do SLA (em dia/estourado)
     - Grafo de movimentação do ticket
"""

import pandas as pd
import streamlit as st

from components import kpi, separador
from data import carregar_movimentacoes


def render(df):
    """Renderiza a página Visão Geral do dashboard."""
    st.title('📊 Visão Geral')
    st.markdown(
        'Acompanhamento geral dos tickets: volume, distribuição por categoria, '
        'SLA e busca rápida por ticket específico.'
    )

    if df.empty:
        st.info('Nenhum ticket disponível.')
        return

    # ============================================================
    # 1. RESUMO GERAL (KPIs)
    # ============================================================
    st.markdown('## 📊 Resumo Geral')

    total_tickets = len(df)

    # Contadores com status normalizado (banco usa 'Em atendimento', 'Fechado', etc.)
    if 'status' in df.columns:
        status_norm = df['status'].astype(str).str.strip().str.lower()
        encerrados = {'resolvido', 'fechado', 'cancelado', 'duplicado'}
        tickets_fechados = int(status_norm.isin({'resolvido', 'fechado'}).sum())
        tickets_abertos = int((~status_norm.isin(encerrados)).sum())
    else:
        tickets_abertos = 0
        tickets_fechados = 0

    # SLA
    df_sla = df[
        df['previsao'].notna() & df['data_resolvido'].notna()
    ].copy()
    sla_cumprido = 0
    sla_estourado = 0
    if not df_sla.empty:
        df_sla['data_resolvido'] = pd.to_datetime(df_sla['data_resolvido'], errors='coerce')
        df_sla['previsao'] = pd.to_datetime(df_sla['previsao'], errors='coerce')
        sla_cumprido = int((df_sla['data_resolvido'] <= df_sla['previsao']).sum())
        sla_estourado = int((df_sla['data_resolvido'] > df_sla['previsao']).sum())

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        kpi('Total de Tickets', f'{total_tickets}', icone='inbox')
    with col2:
        kpi(
            'Tickets Abertos',
            f'{tickets_abertos}',
            icone='clock',
            pill_tipo='warning' if tickets_abertos > 0 else 'success',
        )
    with col3:
        kpi(
            'Tickets Resolvidos',
            f'{tickets_fechados}',
            icone='check-circle',
            pill_tipo='success',
        )
    with col4:
        kpi(
            'SLA Cumprido',
            f'{sla_cumprido}',
            icone='check-circle',
            pill_tipo='success',
        )
    with col5:
        kpi(
            'SLA Estourado',
            f'{sla_estourado}',
            icone='alert-triangle',
            pill_tipo='danger' if sla_estourado > 0 else 'success',
        )

    # Reconciliação: SLA só é calculável para tickets resolvidos COM previsão
    total_sla = sla_cumprido + sla_estourado
    sem_sla = total_tickets - total_sla
    if sem_sla > 0:
        st.caption(
            f'ℹ️ SLA calculado para {total_sla} de {total_tickets} tickets. '
            f'{sem_sla} ticket(s) fora do cálculo: ainda não resolvidos '
            f'ou sem previsão de prazo definida.'
        )

    separador()

    # ============================================================
    # 2. DISTRIBUIÇÃO POR CATEGORIA
    # ============================================================
    st.markdown('## 📈 Distribuição por Categoria')

    if 'categoria' in df.columns and not df['categoria'].isna().all():
        dist_cat = df['categoria'].value_counts().head(10).reset_index()
        dist_cat.columns = ['Categoria', 'Quantidade']

        col_cat1, col_cat2 = st.columns([2, 1])

        with col_cat1:
            import plotly.express as px
            fig = px.bar(
                dist_cat,
                x='Categoria',
                y='Quantidade',
                color='Quantidade',
                color_continuous_scale='Blues',
                text='Quantidade',
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_cat2:
            st.markdown('### Top Categorias')
            for _, row in dist_cat.head(8).iterrows():
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'padding:4px 0;border-bottom:1px solid rgba(255,255,255,.05);">'
                    f'<span>{row["Categoria"]}</span>'
                    f'<span><b>{row["Quantidade"]}</b></span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info('Não há dados de categoria disponíveis.')

    separador()

    # ============================================================
    # 3. PESQUISA POR TICKET ESPECÍFICO
    # ============================================================
    st.markdown('## 🔍 Pesquisar Ticket')
    st.markdown(
        'Digite o ID do ticket para ver detalhes, status do SLA e '
        'histórico de movimentação.'
    )

    col_busca1, col_busca2 = st.columns([3, 1])

    with col_busca1:
        ticket_id_input = st.text_input(
            'ID do Ticket',
            placeholder='Ex: 112233',
            key='visao_geral_ticket_id',
            label_visibility='collapsed',
        )

    with col_busca2:
        buscar = st.button(
            'Buscar',
            use_container_width=True,
            type='primary',
            key='btn_buscar_ticket',
        )

    # ==================== EXIBIÇÃO DO TICKET ENCONTRADO ====================
    if 'ticket_detalhe' not in st.session_state:
        st.session_state['ticket_detalhe'] = None

    if buscar and ticket_id_input:
        try:
            ticket_id_int = int(ticket_id_input)
            ticket_encontrado = df[df['id'] == ticket_id_int]

            if ticket_encontrado.empty:
                st.warning(f'Ticket #{ticket_id_input} não encontrado.')
                st.session_state['ticket_detalhe'] = None
            else:
                st.session_state['ticket_detalhe'] = ticket_encontrado.iloc[0].to_dict()
        except ValueError:
            st.warning('Digite um ID numérico válido.')
            st.session_state['ticket_detalhe'] = None

    # Renderiza detalhes se houver ticket selecionado
    if st.session_state.get('ticket_detalhe'):
        ticket = st.session_state['ticket_detalhe']

        st.markdown('---')
        st.markdown(f'## 🎫 Ticket #{ticket.get("id", "-")}')

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.markdown(f'**Título:** {ticket.get("titulo", "-")}')
            st.markdown(f'**Categoria:** {ticket.get("categoria", "-")}')
            st.markdown(f'**Sistema:** {ticket.get("sistema", "-")}')
        with col_t2:
            st.markdown(f'**Status:** {ticket.get("status", "-")}')
            st.markdown(f'**Prioridade:** {ticket.get("prioridade", "-")}')
            st.markdown(f'**Solicitante:** {ticket.get("solicitante", "-")}')
        with col_t3:
            st.markdown(f'**Responsável:** {ticket.get("responsavel_atual", "-")}')
            st.markdown(f'**Empresa:** {ticket.get("empresa", "-")}')
            st.markdown(f'**Criado em:** {ticket.get("criado_data", "-")}')

        # SLA do ticket
        st.markdown('### ⏱️ SLA do Ticket')
        col_sla1, col_sla2, col_sla3 = st.columns(3)

        previsao = ticket.get('previsao')
        data_resolvido = ticket.get('data_resolvido')

        if pd.notna(previsao) and pd.notna(data_resolvido):
            previsao_dt = pd.to_datetime(previsao, errors='coerce')
            resolvido_dt = pd.to_datetime(data_resolvido, errors='coerce')
            sla_ok = resolvido_dt <= previsao_dt
            atraso = (resolvido_dt - previsao_dt).total_seconds() / 3600 if not sla_ok else 0

            with col_sla1:
                kpi(
                    'Status SLA',
                    '✅ Dentro do prazo' if sla_ok else '❌ Estourado',
                    pill_tipo='success' if sla_ok else 'danger',
                )
            with col_sla2:
                kpi(
                    'Previsão',
                    previsao_dt.strftime('%d/%m/%Y %H:%M') if pd.notna(previsao_dt) else '-',
                )
            with col_sla3:
                kpi(
                    'Resolvido em',
                    resolvido_dt.strftime('%d/%m/%Y %H:%M') if pd.notna(resolvido_dt) else '-',
                )
        elif pd.notna(previsao) and pd.isna(data_resolvido):
            previsao_dt = pd.to_datetime(previsao, errors='coerce')
            agora = pd.Timestamp.now()
            sla_ok = agora <= previsao_dt
            with col_sla1:
                kpi(
                    'Status SLA',
                    '✅ Em andamento (dentro do prazo)' if sla_ok else '⚠️ Próximo do vencimento',
                    pill_tipo='success' if sla_ok else 'warning',
                )
            with col_sla2:
                kpi(
                    'Previsão',
                    previsao_dt.strftime('%d/%m/%Y %H:%M') if pd.notna(previsao_dt) else '-',
                )
            with col_sla3:
                kpi(
                    'Status',
                    'Aberto / Não resolvido',
                    pill_tipo='warning',
                )
        else:
            st.info('Ticket sem previsão de SLA definida.')

        # ==================== GRAFO DE MOVIMENTAÇÃO ====================
        st.markdown('### 🔄 Histórico de Movimentações')

        df_movs = carregar_movimentacoes()

        if df_movs.empty:
            st.info('Não há movimentações registradas no banco.')
        else:
            df_movs['data_movimentacao'] = pd.to_datetime(df_movs['data_movimentacao'], errors='coerce')
            df_movs['ticket_id'] = df_movs['ticket_id'].astype(str)
            ticket_id_str = str(ticket.get('id'))
            movs_ticket = df_movs[df_movs['ticket_id'] == ticket_id_str].sort_values('data_movimentacao')

            if movs_ticket.empty:
                st.info('Este ticket ainda não possui movimentações registradas.')
            else:
                # Tabela de movimentações
                tabela_movs = movs_ticket[
                    ['data_movimentacao', 'autor', 'tipo', 'de_status', 'para_status', 'comentario']
                ].copy()
                tabela_movs.columns = [
                    'Data/Hora', 'Autor', 'Tipo', 'De Status', 'Para Status', 'Comentário'
                ]
                tabela_movs['Data/Hora'] = tabela_movs['Data/Hora'].dt.strftime('%d/%m/%Y %H:%M')

                st.dataframe(tabela_movs, use_container_width=True, hide_index=True)

                # Grafo de fluxo simples
                st.markdown('### 🔄 Fluxo de Status do Ticket')

                # Construir sequência de status
                fluxo = movs_ticket[['data_movimentacao', 'para_status']].dropna().sort_values('data_movimentacao')
                if not fluxo.empty:
                    status_sequence = [fluxo['para_status'].iloc[0]]
                    for _, row in fluxo.iterrows():
                        if row['para_status'] != status_sequence[-1]:
                            status_sequence.append(row['para_status'])

                    # Remover duplicatas consecutivas
                    status_unico = []
                    for s in status_sequence:
                        if not status_unico or status_unico[-1] != s:
                            status_unico.append(s)

                    # Exibir como fluxo horizontal
                    st.markdown('**Fluxo de status do ticket:**')
                    fluxo_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">'
                    for i, s in enumerate(status_unico):
                        cor = '#2ecc71' if s in ['Resolvido', 'Fechado'] else '#e74c3c' if s == 'Cancelado' else '#3498db'
                        fluxo_html += (
                            f'<div style="display:flex;align-items:center;gap:6px;">'
                            f'<div style="background:{cor};color:#fff;padding:6px 12px;border-radius:20px;font-size:12px;font-weight:600;">'
                            f'{s}</div>'
                        )
                        if i < len(status_unico) - 1:
                            fluxo_html += f'<span style="color:#c9a666;">➜</span>'
                        fluxo_html += '</div>'
                    fluxo_html += '</div>'
                    st.markdown(fluxo_html, unsafe_allow_html=True)

                    # Linha do tempo detalhada
                    st.markdown('**Linha do tempo detalhada:**')
                    for _, mov in movs_ticket.iterrows():
                        data_str = mov['data_movimentacao'].strftime('%d/%m/%Y %H:%M') if pd.notna(mov['data_movimentacao']) else '-'
                        comentario = str(mov['comentario'])[:80] + ('...' if len(str(mov['comentario'])) > 80 else '') if pd.notna(mov['comentario']) else ''
                        st.markdown(
                            f'<div style="display:flex;align-items:flex-start;gap:12px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05);">'
                            f'<div style="flex-shrink:0;color:#c9a666;font-size:12px;">{data_str}</div>'
                            f'<div style="flex:1;">'
                            f'<div style="font-weight:600;color:#eae7e1;">{mov["autor"]}</div>'
                            f'<div style="font-size:12px;color:#94a3b8;">{mov["de_status"]} → {mov["para_status"]}</div>'
                            f'<div style="font-size:12px;color:#94a3b8;margin-top:2px;">{comentario}</div>' if comentario else ''
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.info('Não há histórico de movimentação para este ticket.')
    else:
        st.info('Digite um ID de ticket acima para visualizar os detalhes.')


# Para teste standalone
if __name__ == '__main__':
    import pandas as pd
    df_test = pd.DataFrame({
        'id': [1, 2, 3],
        'titulo': ['Ticket 1', 'Ticket 2', 'Ticket 3'],
        'categoria': ['A', 'B', 'A'],
        'status': ['Aberto', 'Fechado', 'Em Atendimento'],
        'criado_data': pd.to_datetime(['2026-01-01', '2026-01-02', '2026-01-03']),
        'data_resolvido': pd.to_datetime([None, '2026-01-05', None]),
        'previsao': pd.to_datetime(['2026-01-10', '2026-01-04', '2026-01-15']),
        'solicitante': ['User 1', 'User 2', 'User 3'],
        'responsavel_atual': ['Ana', 'Bob', 'Ana'],
        'sistema': ['SIGEPREV', 'SIGEPREV', 'Help360'],
    })
    render(df_test)